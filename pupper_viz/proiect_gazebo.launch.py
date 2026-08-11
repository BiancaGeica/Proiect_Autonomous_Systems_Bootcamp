import os
import re
import xml.etree.ElementTree as ET
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    
    # Calea către fișierul xacro de gazebo
    xacro_path = os.path.join(os.path.dirname(__file__), "pupper_v3_gazebo.urdf.xacro")
    
    # Generăm URDF-ul brut prin comanda xacro
    raw_urdf_bytes = os.popen(f"xacro {xacro_path}").read()
    
    # Factorul de scară dorit (1.0 = 100% (original), 1.2 = 120%)
    SCALE_FACTOR = 5

    # Curățare preliminară pentru erorile specifice din fișier
    def pre_clean_urdf(xml_str):
        xml_str = re.sub(r'<joint\s+name="(leg_[^"]+)"', r'<joint name="\1_joint"', xml_str)
        xml_str = re.sub(r'<link\s+name="world"\s*(/>|>[^<]*</link>)', '', xml_str)
        xml_str = re.sub(r'<joint\s+name="world_to_body"[\s\S]*?</joint>', '', xml_str)
        return xml_str

    # Scalare structurală XML 100% garantată pe orice axă și orice picior
    def scale_urdf_xml(xml_str, scale):
        cleaned_str = pre_clean_urdf(xml_str)
        
        # Parsăm string-ul XML într-un arbore de elemente
        root = ET.fromstring(cleaned_str)

        # 1. Scalăm toate originile (<origin xyz="x y z"/>)
        for origin in root.findall(".//origin"):
            if 'xyz' in origin.attrib:
                try:
                    coords = [float(c) * scale for c in origin.attrib['xyz'].split()]
                    origin.attrib['xyz'] = f"{coords[0]} {coords[1]} {coords[2]}"
                except ValueError:
                    pass

        # 2. Scalăm geometriile 3D (<mesh filename="..." scale="x y z"/>)
        for mesh in root.findall(".//mesh"):
            if 'scale' in mesh.attrib:
                try:
                    s_vals = [float(s) * scale for s in mesh.attrib['scale'].split()]
                    mesh.attrib['scale'] = f"{s_vals[0]} {s_vals[1]} {s_vals[2]}"
                except ValueError:
                    mesh.attrib['scale'] = f"{scale} {scale} {scale}"
            else:
                mesh.attrib['scale'] = f"{scale} {scale} {scale}"

        # 3. Scalăm formele primitive (<box size="x y z"/>)
        for box in root.findall(".//box"):
            if 'size' in box.attrib:
                try:
                    sizes = [float(s) * scale for s in box.attrib['size'].split()]
                    box.attrib['size'] = f"{sizes[0]} {sizes[1]} {sizes[2]}"
                except ValueError:
                    pass

        # 4. Scalarea cilindrilor (<cylinder radius="r" length="l"/>)
        for cylinder in root.findall(".//cylinder"):
            if 'radius' in cylinder.attrib:
                try:
                    cylinder.attrib['radius'] = str(float(cylinder.attrib['radius']) * scale)
                except ValueError:
                    pass
            if 'length' in cylinder.attrib:
                try:
                    cylinder.attrib['length'] = str(float(cylinder.attrib['length']) * scale)
                except ValueError:
                    pass

        # Reconvertim arborele XML modificat înapoi în string
        return ET.tostring(root, encoding='utf-8').decode('utf-8')

    cleaned_urdf = scale_urdf_xml(raw_urdf_bytes, SCALE_FACTOR)
    
    robot_description = {
        "robot_description": ParameterValue(cleaned_urdf, value_type=str)
    }
    
    rviz_config_file = PathJoinSubstitution(
        [os.path.dirname(__file__), "rviz_config.rviz"]
    )

    # Setăm robust căile de resurse pentru Gazebo Harmonic (inclusiv pachetele din src)
    try:
        pupper_share = get_package_share_directory('pupper_v3_description')
        ws_root = os.path.dirname(os.path.dirname(os.path.dirname(pupper_share)))
    except Exception:
        ws_root = '/ws'

    extra_paths = [
        os.path.join(ws_root, 'src'),
        os.path.join(ws_root, 'install'),
        '/ws/src',
        '/ws/install'
    ]
    
    existing_gz_path = os.environ.get('GZ_SIM_RESOURCE_PATH', '')
    new_gz_path = os.pathsep.join([existing_gz_path] + extra_paths)

    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=new_gz_path
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

    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="lidar_static_tf_publisher",
        arguments=[
            "0.0", "0.0", "0.25",
            "0.0", "0.0", "0.0",
            "base_link",
            "hokuyo_link"
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

    gazebo_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                '/opt/ros/jazzy/share/ros_gz_sim/launch/gz_sim.launch.py'
            ])
        ]),
        launch_arguments={'gz_args': '-r shapes.sdf'}.items()
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'pupper_v3',
            '-x', '-2.0',  # Mută robotul la 2 metri în spatele originii (pe axa X negativă)
            '-y', '0.0',
            '-z', '1.0'    # Îl menținem la 1 metru înălțime pentru a evita intersecția inițială
        ],
        output='screen'
    )

    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan'
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