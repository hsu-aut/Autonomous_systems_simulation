# Starts the read-only robot monitor window.
#
#   ros2 launch neo_robot_monitor monitor.launch.py
#   ros2 launch neo_robot_monitor monitor.launch.py tcp_frame:=right_inner_finger_pad
#
# use_sim_time defaults to True because this is normally run against the Gazebo
# simulation; with it false the TF lookups are made against the wall clock and every
# transform looks unusably old, so all poses show as unavailable.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='True',
                              description='Use the /clock topic (True in simulation)'),
        DeclareLaunchArgument('map_frame', default_value='map'),
        DeclareLaunchArgument('odom_frame', default_value='odom'),
        DeclareLaunchArgument('base_frame', default_value='base_link'),
        DeclareLaunchArgument(
            'tcp_frame', default_value='ur10tool0',
            description='End-effector frame. ur10tool0 is the UR tool flange; use '
                        'grasp_tcp for the grasp centre between the finger pads.'),
        Node(
            package='neo_robot_monitor',
            executable='monitor',
            name='neo_robot_monitor',
            output='screen',
            parameters=[{
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'map_frame': LaunchConfiguration('map_frame'),
                'odom_frame': LaunchConfiguration('odom_frame'),
                'base_frame': LaunchConfiguration('base_frame'),
                'tcp_frame': LaunchConfiguration('tcp_frame'),
            }],
        ),
    ])
