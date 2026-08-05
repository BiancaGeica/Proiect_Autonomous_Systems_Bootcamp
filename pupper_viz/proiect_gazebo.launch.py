import os
import re
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    
    # Calea către fișierul xacro de gazebo
    xacro_path = os.path.join(os.path.dirname(__file__), "pupper_v3_gazebo.urdf.xacro")
    
    # Generăm URDF-ul brut prin comanda xacro și aplicăm o funcție de curățare a denumirilor
    raw_urdf_bytes = os.popen(f"xacro {xacro_path}").read()
    
    # Curățăm conflictele de nume și eliminăm legăturile problematice pentru Gazebo
    def fix_urdf_names(xml_str):
        # 1. Adăugăm sufixul _joint la picioare (cum aveai înainte)
        xml_str = re.sub(r'<joint\s+name="(leg_[^"]+)"', r'<joint name="\1_joint"', xml_str)
        
        # 2. ȘTERGEM link-ul 'world'
        xml_str = re.sub(r'<link\s+name="world"\s*(/>|>[^<]*</link>)', '', xml_str)
        
        # 3. ȘTERGEM joint-ul 'world_to_body' care provoacă crash-ul în Gazebo
        xml_str = re.sub(r'<joint\s+name="world_to_body"[\s\S]*?</joint>', '', xml_str)
        
        return xml_str

    cleaned_urdf = fix_urdf_names(raw_urdf_bytes)
    
    robot_description = {
        "robot_description": ParameterValue(cleaned_urdf, value_type=str)
    }
    
    rviz_config_file = PathJoinSubstitution(
        [os.path.dirname(__file__), "rviz_config.rviz"]
    )

    # Setăm calea de resurse pentru ca Gazebo să găsească mesh-urile STL
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=['/ws/src:', '/ws/install:']
    )

    # Nodurile principale
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description, {'use_sim_time': True}],
    )
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[{'use_sim_time': True}],
    )

    dummy_laser_node = Node(
        package="dummy_sensors",
        executable="dummy_laser",
        name="dummy_laser",
        output="screen",
        parameters=[{'use_sim_time': True}],
    )

    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="lidar_static_tf_publisher",
        arguments=[
            "0.0", "0.0", "0.1",
            "0.0", "0.0", "0.0",
            "base_link",
            "single_rrbot_hokuyo_link"
        ],
        parameters=[{'use_sim_time': True}],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["forward_command_controller", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'base_frame': 'base_link',
            'odom_frame': 'odom',
            'map_frame': 'map',
            'scan_topic': '/scan',
            'mode': 'mapping',
            'transform_timeout': 1.0,
            'minimum_travel_distance': 0.0,
            'minimum_travel_heading': 0.0,
            'map_update_interval': 0.5,
        }]
    )

    odom_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="odom_static_tf_publisher",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "odom", "base_link"],
        parameters=[{'use_sim_time': True}],
        output="screen"
    )

    initial_map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='initial_map_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': '/work/empty_map.yaml'
        }]
    )

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_initial_map',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['initial_map_server']
        }]
    )
    
    map_to_odom_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="map_to_odom_publisher",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "map", "odom"],
        parameters=[{'use_sim_time': True}],
        output="screen"
    )

    # Gazebo Simulator (lumea shapes.sdf)
    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                '/opt/ros/jazzy/share/ros_gz_sim/launch/gz_sim.launch.py'
            ])
        ]),
        launch_arguments={'gz_args': '-r shapes.sdf'}.items()
    )

    # Spawnează modelul Pupper folosind topicul robot_description
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'pupper_v3',
            '-z', '0.2'
        ],
        output='screen'
    )

    # Puntea de comunicare ROS 2 <-> Gazebo
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    nodes = [
        set_gz_resource_path,
        robot_state_pub_node,                              
        joint_state_broadcaster_spawner,                  
        robot_controller_spawner,
        rviz_node,                                            
        dummy_laser_node,                                     
        static_tf_node,                                      
        slam_node,                                          
        odom_tf_node,                                      
        initial_map_server,
        lifecycle_manager_node,
        map_to_odom_tf,
        gazebo_sim,
        spawn_robot,
        ros_gz_bridge,
    ]

    return LaunchDescription(nodes)