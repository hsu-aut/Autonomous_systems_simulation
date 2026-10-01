# Neobotix GmbH - combined bringup
#
# Brings up the whole stack from a single launch file:
#
#   1. simulation.launch.py            (Gazebo + robot + ros2_control)
#   2. navigation.launch.py + RViz     (nav2 stack and its map view)
#   3. neo_ur_moveit.launch.py         (move_group + MoveIt RViz)
#   4. neo_robot_monitor               (joint / pose window)
#
# Every part is a launch argument, so this is the ONLY combined launch file:
#
#   everything                         bringup.launch.py use_nav_rviz:=True
#   default (no navigation RViz)       bringup.launch.py
#   navigation only, no MoveIt         bringup.launch.py use_moveit:=False use_moveit_rviz:=False
#   no arm at all                      bringup.launch.py arm_type:="" use_moveit:=False
#   headless, no windows               bringup.launch.py gui:=False use_nav_rviz:=False
#                                        use_moveit_rviz:=False use_monitor:=False
#
# (sim_navigation.launch.py used to be the "no MoveIt" variant; it was this file
# minus one include and has been removed.)
#
# Ordering matters and is enforced with TimerAction. navigation and MoveIt both
# need the simulation fully up first:
#   - navigation.launch.py reads robot_name.txt, which simulation.launch.py writes
#   - MoveIt binds to /joint_trajectory_controller and /robotiq_gripper_controller
#     (through gripper_action_relay), which only exist once gazebo_ros2_control has
#     started controller_manager
# Starting them too early reproduces the classic 'Invalid frame ID "odom"' flood or
# 'Action client not connected to action server'. If your machine is slow, raise
# nav_delay / moveit_delay rather than launching things by hand.
#
# Examples:
#   ros2 launch neo_simulation2 bringup.launch.py
#   ros2 launch neo_simulation2 bringup.launch.py world:=neo_track1 map:=neo_track1
#   ros2 launch neo_simulation2 bringup.launch.py use_moveit:=False
#   ros2 launch neo_simulation2 bringup.launch.py use_navigation:=False
#   ros2 launch neo_simulation2 bringup.launch.py nav_delay:=30.0 moveit_delay:=35.0

from ament_index_python.packages import (get_package_share_directory,
                                          PackageNotFoundError)
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            TimerAction, LogInfo, OpaqueFunction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def monitor_actions(context, use_monitor, tcp_frame):
    """The monitor is optional, so a missing package must not kill the launch.

    FindPackageShare raises when neo_robot_monitor is not on AMENT_PREFIX_PATH -
    which happens simply by having sourced install/setup.bash before the package was
    built - and that exception aborts the *whole* launch, tearing down Gazebo, nav2 and
    MoveIt with it. Resolving the package here lets us skip it with a clear message.
    """
    if context.perform_substitution(use_monitor).lower() not in ('true', '1', 'yes'):
        return []
    try:
        get_package_share_directory('neo_robot_monitor')
    except PackageNotFoundError:
        return [LogInfo(msg='[bringup] neo_robot_monitor not found on '
                            'AMENT_PREFIX_PATH - skipping the monitor window. '
                            'Build it and re-source install/setup.bash, or pass '
                            'use_monitor:=False to silence this.')]
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution(
                [FindPackageShare('neo_robot_monitor'), 'launch', 'monitor.launch.py'])),
            launch_arguments={
                'use_sim_time': 'True',
                'tcp_frame': tcp_frame,
            }.items(),
        ),
    ]


def generate_launch_description():

    my_robot       = LaunchConfiguration('my_robot')
    world          = LaunchConfiguration('world')
    arm_type       = LaunchConfiguration('arm_type')
    map_name       = LaunchConfiguration('map')
    use_moveit     = LaunchConfiguration('use_moveit')
    use_navigation = LaunchConfiguration('use_navigation')
    use_nav_rviz   = LaunchConfiguration('use_nav_rviz')
    use_moveit_rviz = LaunchConfiguration('use_moveit_rviz')
    use_monitor    = LaunchConfiguration('use_monitor')
    rviz_delay     = LaunchConfiguration('rviz_delay')
    monitor_delay  = LaunchConfiguration('monitor_delay')
    tcp_frame      = LaunchConfiguration('tcp_frame')
    nav_delay      = LaunchConfiguration('nav_delay')
    moveit_delay   = LaunchConfiguration('moveit_delay')

    declared_arguments = [
        DeclareLaunchArgument(
            'my_robot', default_value='mpo_700',
            description='Robot Types: "mpo_700", "mpo_500", "mp_400", "mp_500"'),
        DeclareLaunchArgument(
            'world', default_value='neo_workshop',
            description='Gazebo world: "neo_workshop", "neo_track1", or "neo_table" (one big table in front '
                        'of the robot, no walls - pair it with use_navigation:=False)'),
        DeclareLaunchArgument(
            'arm_type', default_value='ur10',
            description='UR arm: ur5, ur10, ur5e, ur10e, or "none" for no arm (MoveIt and '
                        'the monitor\'s TCP then have nothing to attach to; pass '
                        'use_moveit:=False as well).'),
        DeclareLaunchArgument(
            'map', default_value='neo_workshop',
            description='Map name from neo_simulation2/maps, or a full path to a .yaml'),
        DeclareLaunchArgument(
            'use_navigation', default_value='True',
            description='Start the nav2 stack'),
        DeclareLaunchArgument(
            'use_nav_rviz', default_value='False',
            description='Start RViz with the navigation view. Off by default; RViz is the '
                        'heaviest component on the machine.'),
        DeclareLaunchArgument(
            'use_moveit', default_value='True',
            description='Start move_group (requires a non-empty arm_type)'),
        DeclareLaunchArgument(
            'use_moveit_rviz', default_value='True',
            description='Start the MoveIt motion planning RViz'),
        DeclareLaunchArgument(
            'gui', default_value='True',
            description='Start the Gazebo GUI. False runs the simulation headless.'),
        DeclareLaunchArgument(
            'gui_delay', default_value='6.0',
            description='Seconds after gzserver before the Gazebo GUI starts, so its scene request '
                        'cannot beat the world load (a blank window otherwise).'),
        DeclareLaunchArgument(
            'use_teleop', default_value='False',
            description='Start teleop_twist_keyboard in an xterm (it rarely gets focus; '
                        'running it in your own terminal works better).'),
        DeclareLaunchArgument(
            'use_monitor', default_value='True',
            description='Start the neo_robot_monitor window (joint states, base pose, '
                        'TCP pose)'),
        DeclareLaunchArgument(
            'tcp_frame', default_value='ur10tool0',
            description='End-effector frame shown by the monitor. ur10tool0 is the UR '
                        'tool flange; grasp_tcp is the grasp centre between the pads.'),
        DeclareLaunchArgument(
            'nav_delay', default_value='20.0',
            description='Seconds to wait for the simulation before starting navigation'),
        DeclareLaunchArgument(
            'rviz_delay', default_value='32.0',
            description='Seconds before starting the navigation RViz. Deliberately well '
                        'after nav_delay: RViz is heavy to start and, launched at the '
                        'same moment as the nav2 stack, it starves the lifecycle manager '
                        'while it is activating map_server - leaving map_server stuck in '
                        '"unconfigured" and RViz with no map.'),
        DeclareLaunchArgument(
            'monitor_delay', default_value='36.0',
            description='Seconds before starting the monitor window, staggered after '
                        'RViz for the same reason.'),
        DeclareLaunchArgument(
            'moveit_delay', default_value='26.0',
            description='Seconds to wait for the simulation before starting MoveIt. '
                        'Must be long enough for the controllers to activate.'),
    ]

    # ------------------------------------------------------------------ simulation
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution(
            [FindPackageShare('neo_simulation2'), 'launch', 'simulation.launch.py'])),
        launch_arguments={
            'my_robot': my_robot,
            'world': world,
            'arm_type': arm_type,
            'use_teleop': LaunchConfiguration('use_teleop'),
            'gui': LaunchConfiguration('gui'),
            'gui_delay': LaunchConfiguration('gui_delay'),
        }.items(),
    )

    # ------------------------------------------------------------------ navigation
    navigation = TimerAction(
        period=nav_delay,
        actions=[
            LogInfo(msg='[bringup] starting navigation'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(PathJoinSubstitution(
                    [FindPackageShare('neo_simulation2'), 'launch',
                     'navigation.launch.py'])),
                launch_arguments={
                    'map': map_name,
                    'use_sim_time': 'True',
                }.items(),
            ),
        ],
        condition=IfCondition(use_navigation),
    )

    # Uses neo_simulation2/rviz/navigation.rviz, NOT neo_nav2_bringup's
    # single_robot.rviz. The latter is a template containing 16 "<robot_namespace>"
    # placeholders that nav2_bringup's rviz_launch.py substitutes at runtime; passed
    # straight to rviz2 the '<' and '>' are illegal in topic names, so RViz rejects the
    # whole config with "Could not load display config: Invalid topic name" and comes up
    # completely blank. navigation.rviz is that config with the placeholders resolved
    # for the un-namespaced case, and with the left dock un-hidden so the Displays panel
    # (and any errors in it) are actually visible.
    #
    # use_sim_time is required as well, or RViz's message filters discard every scan and
    # transform as stale against the wall clock.
    nav_rviz = TimerAction(
        period=rviz_delay,
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2_navigation',
                output='log',
                arguments=['-d', PathJoinSubstitution(
                    [FindPackageShare('neo_simulation2'), 'rviz', 'navigation.rviz'])],
                parameters=[{'use_sim_time': True}],
            ),
        ],
        condition=IfCondition(use_nav_rviz),
    )

    # ---------------------------------------------------------------------- moveit
    moveit = TimerAction(
        period=moveit_delay,
        actions=[
            LogInfo(msg='[bringup] starting MoveIt'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(PathJoinSubstitution(
                    [FindPackageShare('neo_ur_moveit_config'), 'launch',
                     'neo_ur_moveit.launch.py'])),
                launch_arguments={
                    'ur_type': arm_type,
                    'my_robot': my_robot,
                    'prefix': arm_type,      # neo_simulation2 derives tf_prefix from arm_type
                    'use_gazebo': 'true',    # selects the neo_simulation2 URDF
                    'use_sim_time': 'true',  # required for trajectory execution in sim
                    'launch_rviz': use_moveit_rviz,
                }.items(),
            ),
        ],
        condition=IfCondition(use_moveit),
    )

    # Shares the navigation timer: the monitor reads /joint_states and looks up TF
    # map->base_link, so it has nothing to show until the controllers are active and
    # navigation has published a map.
    monitor = TimerAction(
        period=monitor_delay,
        actions=[OpaqueFunction(function=monitor_actions,
                                args=[use_monitor, tcp_frame])],
    )

    return LaunchDescription(
        declared_arguments + [simulation, navigation, nav_rviz, moveit, monitor])
