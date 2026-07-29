"""Viz-only mock of CS123 Lab 2 (no robot hardware).

robot_state_publisher (model) + joint_state_publisher_gui (leg sliders)
+ lab_2.py (forward-kinematics marker) + rviz2.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("pupper_v3_description")
    urdf_path = os.path.join(
        share, "description", "urdf", "pupper_v3.edited.fixed.urdf"
    )
    with open(urdf_path, "r") as f:
        robot_description = f.read()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
    )

    # The lab's FK node, run as a plain script. It subscribes to /joint_states
    # (from the GUI) and publishes /marker (the green end-effector sphere).
    fk_node = ExecuteProcess(
        cmd=["python3", "/work/lab_2.py"],
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", "/work/lab_2.rviz"],
        output="screen",
    )

    return LaunchDescription(
        [robot_state_publisher, joint_state_publisher_gui, fk_node, rviz]
    )
