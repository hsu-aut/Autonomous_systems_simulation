"""Put the objects from config/objects.yaml into the running Gazebo simulation.

    ros2 launch neo_sim_objects spawn_objects.launch.py
    ros2 launch neo_sim_objects spawn_objects.launch.py objects:=/path/to/my_objects.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default = os.path.join(get_package_share_directory('neo_sim_objects'),
                           'config', 'objects.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('objects', default_value=default,
                              description='File listing the objects to put into Gazebo'),
        Node(package='neo_sim_objects', executable='spawn_objects', name='spawn_objects',
             output='both',
             parameters=[LaunchConfiguration('objects'), {'use_sim_time': True}]),
    ])
