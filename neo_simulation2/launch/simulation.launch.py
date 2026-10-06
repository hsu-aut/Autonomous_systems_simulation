# Neobotix GmbH - start command of the original package
#
# Starts the same as bringup.launch.py: it only includes that file. Every argument of
# bringup.launch.py works here as well (navigation_rviz, moveit_rviz, teleop, world,
# map, spawn_cube, the delays, ...), with the same defaults: everything except Gazebo
# and the cube is off.
#
# The arguments are not passed on one by one: arguments given on the command line are
# launch configurations of the whole launch, and the included bringup.launch.py reads
# them directly. --show-args lists the arguments of bringup.launch.py.
#
# Gazebo and the robot alone (no cube, no navigation, no MoveIt) are started by
# gazebo_robot.launch.py, which bringup.launch.py includes first.
#
# Examples:
#   ros2 launch neo_simulation2 simulation.launch.py
#   ros2 launch neo_simulation2 simulation.launch.py navigation_rviz:=True moveit_rviz:=True
#   ros2 launch neo_simulation2 simulation.launch.py --show-args

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution(
                [FindPackageShare('neo_simulation2'), 'launch', 'bringup.launch.py']))),
    ])
