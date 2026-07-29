from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch.actions import ExecuteProcess

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

import os


def generate_launch_description():
    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    os.path.dirname(__file__),
                    "pupper_v3_mock.urdf.xacro",
                ]
            ),
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution(
        [
            os.path.dirname(__file__),
            "lab_4.yaml",
        ]
    )
    rviz_config_file = PathJoinSubstitution(
        [os.path.dirname(__file__), "rviz_config.rviz"]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        output="both",
    )
    
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    # -------------------------------------------------------------
    # ADĂUGAT: Nodul pentru LiDAR-ul artificial (dummy_laser)
    # -------------------------------------------------------------
    dummy_laser_node = Node(
        package="dummy_sensors",
        executable="dummy_laser",
        name="dummy_laser",
        output="screen",
    )

    # -------------------------------------------------------------
    # ADĂUGAT: Transformare TF statică între base_link și LiDAR
    # Modifică x, y, z dacă vrei ca LiDAR-ul să fie într-o poziție anume pe robot.
    # -------------------------------------------------------------
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="lidar_static_tf_publisher",
        arguments=[
            "--x", "0.0",
            "--y", "0.0",
            "--z", "0.1",
            "--yaw", "0.0",
            "--pitch", "0.0",
            "--roll", "0.0",
            "--frame-id", "base_link",
            "--child-frame-id", "single_rrbot_hokuyo_link",
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    imu_sensor_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["imu_sensor_broadcaster", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["forward_command_controller", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "30"],
    )

    #Nodul SLAM Toolbox
    slam_node = Node(
    package='slam_toolbox',
    executable='async_slam_toolbox_node',
    name='slam_toolbox',
    output='screen',
    parameters=[{
        'use_sim_time': False,
        'base_frame': 'base_link',
        'odom_frame': 'odom',
        'map_frame': 'map',
        'scan_topic': '/scan',
        'mode': 'mapping'
    }]
    )

    # TF Static temporar pentru Odometrie
    odom_tf_node = Node(
    package="tf2_ros",
    executable="static_transform_publisher",
    name="odom_static_tf_publisher",
    arguments=[
        "--x", "0.0", "--y", "0.0", "--z", "0.0",
        "--yaw", "0.0", "--pitch", "0.0", "--roll", "0.0",
        "--frame-id", "odom",
        "--child-frame-id", "base_link"
    ],
    output="screen"
    )   

    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[robot_controller_spawner],
        )
    )

    ik_node = ExecuteProcess(
        cmd=["python3", "/work/lab_4.py"],
        output="screen",
    )

    

    nodes = [
        control_node,                                      
        robot_state_pub_node,                              
        joint_state_broadcaster_spawner,                  
        #imu_sensor_broadcaster_spawner,                    
        #ik_node,                                          #inverse kinematics , dezactivat
        rviz_node,                                            # Deschide RViz2
        dummy_laser_node,                                     # Deschide senzorul LiDAR artificial
        static_tf_node,                                      # Publică TF-ul dintre base_link și LiDAR
        #delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,
        slam_node,                                          # algoritm SLAM
        odom_tf_node                                        # odometrie
    ]

    return LaunchDescription(nodes)