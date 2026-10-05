# Neobotix GmbH - combined bringup
#
# Brings up the whole stack from a single launch file:
#
#   1. simulation.launch.py            (Gazebo + robot + ros2_control)
#   2. navigation.launch.py + RViz     (nav2 stack and its map view)
#   3. neo_ur_moveit.launch.py         (move_group + MoveIt RViz, moveit:=True)
#   4. neo_robot_monitor               (joint / pose window, monitor:=True)
#   5. neo_sim_objects                 (the cube on the table, spawn_cube:=True)
#
# Every part is a launch argument, named after the part it starts, so this is the ONLY
# combined launch file:
#
#   everything                         bringup.launch.py moveit:=True navigation_rviz:=True monitor:=True
#   default (navigation, no MoveIt,    bringup.launch.py
#            no navigation RViz,
#            no monitor window)
#   navigation and MoveIt              bringup.launch.py moveit:=True
#   no arm at all                      bringup.launch.py arm_type:=""
#   headless, no windows               bringup.launch.py gazebo_gui:=False
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
# navigation_delay / moveit_delay rather than launching things by hand.
#
# Examples:
#   ros2 launch neo_simulation2 bringup.launch.py
#   ros2 launch neo_simulation2 bringup.launch.py world:=neo_track1 map:=neo_track1
#   ros2 launch neo_simulation2 bringup.launch.py moveit:=True
#   ros2 launch neo_simulation2 bringup.launch.py navigation:=False moveit:=True
#   ros2 launch neo_simulation2 bringup.launch.py navigation_delay:=30.0 moveit_delay:=35.0
#   ros2 launch neo_simulation2 bringup.launch.py spawn_cube:=False

import os

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


# Argument names before the renaming, and their new names. ros2 launch silently
# ignores arguments it does not know, so an old name would otherwise do nothing.
RENAMED_ARGUMENTS = {
    'gui': 'gazebo_gui',
    'gui_delay': 'gazebo_gui_delay',
    'use_navigation': 'navigation',
    'use_nav_rviz': 'navigation_rviz',
    'nav_delay': 'navigation_delay',
    'rviz_delay': 'navigation_rviz_delay',
    'use_moveit': 'moveit',
    'use_moveit_rviz': 'moveit_rviz',
    'use_monitor': 'monitor',
    'use_teleop': 'teleop',
}


def renamed_argument_warnings(context):
    """Warn about arguments passed under their old names (they have no effect)."""
    return [LogInfo(msg='[bringup] WARNING: "%s" was renamed to "%s" - "%s:=%s" is ignored.'
                        % (old, new, old, context.launch_configurations[old]))
            for old, new in RENAMED_ARGUMENTS.items()
            if old in context.launch_configurations]


def monitor_actions(context, monitor, tcp_frame):
    """The monitor is optional, so a missing package must not kill the launch.

    FindPackageShare raises when neo_robot_monitor is not on AMENT_PREFIX_PATH -
    which happens simply by having sourced install/setup.bash before the package was
    built - and that exception aborts the *whole* launch, tearing down Gazebo, nav2 and
    MoveIt with it. Resolving the package here lets us skip it with a clear message.
    """
    if context.perform_substitution(monitor).lower() not in ('true', '1', 'yes'):
        return []
    try:
        get_package_share_directory('neo_robot_monitor')
    except PackageNotFoundError:
        return [LogInfo(msg='[bringup] neo_robot_monitor not found on '
                            'AMENT_PREFIX_PATH - skipping the monitor window. '
                            'Build it and re-source install/setup.bash, or leave '
                            'monitor at False to silence this.')]
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


def cube_actions(context, spawn_cube, objects, world):
    """Place the objects, by default the cube on the first cafe table of neo_workshop.

    The default object file holds world coordinates for neo_workshop, so it is only
    used there. spawn_objects moves an object that already exists back to its position
    instead of adding a second one: neo_table.world has its own model named "cube",
    which the default file would carry off that world's table. Other worlds therefore
    get objects only from an explicit objects:=... file.
    spawn_objects runs once and exits; it waits up to 15 s for Gazebo's services.
    """
    if context.perform_substitution(spawn_cube).lower() not in ('true', '1', 'yes'):
        return []
    objects_file = context.perform_substitution(objects)
    world_name = os.path.splitext(os.path.basename(context.perform_substitution(world)))[0]
    if not objects_file:
        if world_name != 'neo_workshop':
            return [LogInfo(msg='[bringup] spawn_cube: the default cube belongs to '
                                'neo_workshop - nothing placed in world "%s". Pass '
                                'objects:=<file> to place objects here.' % world_name)]
        objects_file = os.path.join(
            get_package_share_directory('neo_sim_objects'), 'config', 'objects.yaml')
    return [
        LogInfo(msg='[bringup] placing the objects of %s (spawn_cube)'
                    % os.path.basename(objects_file)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution(
                [FindPackageShare('neo_sim_objects'), 'launch', 'spawn_objects.launch.py'])),
            launch_arguments={'objects': objects_file}.items(),
        ),
    ]


def generate_launch_description():

    my_robot              = LaunchConfiguration('my_robot')
    world                 = LaunchConfiguration('world')
    arm_type              = LaunchConfiguration('arm_type')
    map_name              = LaunchConfiguration('map')
    gazebo_gui            = LaunchConfiguration('gazebo_gui')
    gazebo_gui_delay      = LaunchConfiguration('gazebo_gui_delay')
    teleop                = LaunchConfiguration('teleop')
    navigation            = LaunchConfiguration('navigation')
    navigation_delay      = LaunchConfiguration('navigation_delay')
    navigation_rviz       = LaunchConfiguration('navigation_rviz')
    navigation_rviz_delay = LaunchConfiguration('navigation_rviz_delay')
    moveit                = LaunchConfiguration('moveit')
    moveit_rviz           = LaunchConfiguration('moveit_rviz')
    moveit_delay          = LaunchConfiguration('moveit_delay')
    monitor               = LaunchConfiguration('monitor')
    monitor_delay         = LaunchConfiguration('monitor_delay')
    tcp_frame             = LaunchConfiguration('tcp_frame')
    spawn_cube            = LaunchConfiguration('spawn_cube')
    objects               = LaunchConfiguration('objects')
    cube_delay            = LaunchConfiguration('cube_delay')

    declared_arguments = [
        DeclareLaunchArgument(
            'my_robot', default_value='mpo_700',
            description='Robot Types: "mpo_700", "mpo_500", "mp_400", "mp_500"'),
        DeclareLaunchArgument(
            'world', default_value='neo_workshop',
            description='Gazebo world: "neo_workshop", "neo_track1", or "neo_table" (one big table in front '
                        'of the robot, no walls - pair it with navigation:=False)'),
        DeclareLaunchArgument(
            'arm_type', default_value='ur10',
            description='UR arm: ur5, ur10, ur5e, ur10e, or "none" for no arm (MoveIt and '
                        'the monitor\'s TCP then have nothing to attach to; leave '
                        'moveit at False).'),
        DeclareLaunchArgument(
            'map', default_value='neo_workshop',
            description='Map name from neo_simulation2/maps, or a full path to a .yaml'),
        DeclareLaunchArgument(
            'gazebo_gui', default_value='True',
            description='Start the Gazebo window. False runs the simulation headless.'),
        DeclareLaunchArgument(
            'gazebo_gui_delay', default_value='6.0',
            description='Seconds after gzserver before the Gazebo window starts, so its scene '
                        'request cannot beat the world load (a blank window otherwise).'),
        DeclareLaunchArgument(
            'teleop', default_value='False',
            description='Start teleop_twist_keyboard in an xterm (it rarely gets focus; '
                        'running it in your own terminal works better).'),
        DeclareLaunchArgument(
            'navigation', default_value='True',
            description='Start the nav2 stack'),
        DeclareLaunchArgument(
            'navigation_delay', default_value='20.0',
            description='Seconds to wait for the simulation before starting navigation'),
        DeclareLaunchArgument(
            'navigation_rviz', default_value='False',
            description='Start RViz with the navigation view. Off by default; RViz is the '
                        'heaviest component on the machine.'),
        DeclareLaunchArgument(
            'navigation_rviz_delay', default_value='32.0',
            description='Seconds before starting the navigation RViz. Deliberately well '
                        'after navigation_delay: RViz is heavy to start and, launched at '
                        'the same moment as the nav2 stack, it starves the lifecycle '
                        'manager while it is activating map_server - leaving map_server '
                        'stuck in "unconfigured" and RViz with no map.'),
        DeclareLaunchArgument(
            'moveit', default_value='False',
            description='Start move_group (requires a non-empty arm_type). Off by default; '
                        'pass moveit:=True to plan arm and gripper motions.'),
        DeclareLaunchArgument(
            'moveit_rviz', default_value='True',
            description='Start the MoveIt motion planning RViz'),
        DeclareLaunchArgument(
            'moveit_delay', default_value='26.0',
            description='Seconds to wait for the simulation before starting MoveIt. '
                        'Must be long enough for the controllers to activate.'),
        DeclareLaunchArgument(
            'monitor', default_value='False',
            description='Start the neo_robot_monitor window (joint states, base pose, '
                        'TCP pose). Off by default; one window less on the machine.'),
        DeclareLaunchArgument(
            'monitor_delay', default_value='36.0',
            description='Seconds before starting the monitor window, staggered after '
                        'RViz for the same reason.'),
        DeclareLaunchArgument(
            'tcp_frame', default_value='ur10tool0',
            description='End-effector frame shown by the monitor. ur10tool0 is the UR '
                        'tool flange; grasp_tcp is the grasp centre between the pads.'),
        DeclareLaunchArgument(
            'spawn_cube', default_value='True',
            description='Place objects in Gazebo: in neo_workshop the cube on the first cafe '
                        'table (neo_sim_objects/config/objects.yaml), in other worlds the '
                        'objects of the "objects" file. Other worlds without an "objects" '
                        'file get nothing; neo_table has its own cube in the world file.'),
        DeclareLaunchArgument(
            'objects', default_value='',
            description='Object file for spawn_cube (format: neo_sim_objects/config/'
                        'objects.yaml). Empty: the default cube, in neo_workshop only.'),
        DeclareLaunchArgument(
            'cube_delay', default_value='10.0',
            description='Seconds to wait for Gazebo before placing the objects. Before '
                        'navigation_delay and moveit_delay, so both start with the cube '
                        'in place.'),
    ]

    # ------------------------------------------------------------------ simulation
    simulation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution(
            [FindPackageShare('neo_simulation2'), 'launch', 'simulation.launch.py'])),
        launch_arguments={
            'my_robot': my_robot,
            'world': world,
            'arm_type': arm_type,
            'teleop': teleop,
            'gazebo_gui': gazebo_gui,
            'gazebo_gui_delay': gazebo_gui_delay,
        }.items(),
    )

    # ------------------------------------------------------------------ navigation
    navigation_launch = TimerAction(
        period=navigation_delay,
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
        condition=IfCondition(navigation),
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
    navigation_rviz_launch = TimerAction(
        period=navigation_rviz_delay,
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
        condition=IfCondition(navigation_rviz),
    )

    # ---------------------------------------------------------------------- moveit
    moveit_launch = TimerAction(
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
                    'launch_rviz': moveit_rviz,
                }.items(),
            ),
        ],
        condition=IfCondition(moveit),
    )

    # ----------------------------------------------------------------------- cube
    cube_launch = TimerAction(
        period=cube_delay,
        actions=[OpaqueFunction(function=cube_actions, args=[spawn_cube, objects, world])],
    )

    # Shares the navigation timer: the monitor reads /joint_states and looks up TF
    # map->base_link, so it has nothing to show until the controllers are active and
    # navigation has published a map.
    monitor_launch = TimerAction(
        period=monitor_delay,
        actions=[OpaqueFunction(function=monitor_actions, args=[monitor, tcp_frame])],
    )

    return LaunchDescription(
        [OpaqueFunction(function=renamed_argument_warnings)] + declared_arguments +
        [simulation_launch, cube_launch, navigation_launch, navigation_rviz_launch,
         moveit_launch, monitor_launch])
