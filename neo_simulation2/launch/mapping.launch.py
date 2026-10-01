# Neobotix GmbH
# Author: Pradheep Padmanabhan

import os
from ament_index_python.packages import get_package_share_directory
import launch
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    ld = LaunchDescription()

    param_file_arg = LaunchConfiguration('param_file')

    # Check for the robot with which mapping needs to be done. robot_name.txt lives in
    # the package share directory (written by simulation.launch.py) so that this launch
    # file works from any working directory.
    robot_name_file = os.path.join(
        get_package_share_directory('neo_simulation2'), 'robot_name.txt')

    try:
        with open(robot_name_file, 'r') as file:
            my_neo_robot = file.read().strip()
    except FileNotFoundError:
        raise RuntimeError(
            "Could not find {}.\nStart simulation.launch.py first - it records which "
            "robot was selected.".format(robot_name_file))

    # Declare launch argument for parameter file
    declare_param_file_arg = DeclareLaunchArgument(
        'param_file', 
        default_value = os.path.join(
                get_package_share_directory('neo_simulation2'),
                'configs/' + my_neo_robot,
                'mapping.yaml'),
        description='Param file that needs to be used for navigation, sets according to robot by default'
    )

    ld.add_action(declare_param_file_arg)
    nav2_launch_file_dir = os.path.join(get_package_share_directory('neo_nav2_bringup'), 'launch')
    
    mapping = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([nav2_launch_file_dir, '/mapping.launch.py']),
        launch_arguments={
            'use_sim_time': 'true',
            'param_file': param_file_arg,
        }.items(),
    )

    ld.add_action(mapping)

    return ld
