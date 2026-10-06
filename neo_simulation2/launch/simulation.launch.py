# Neobotix GmbH
# Author: Pradheep Padmanabhan

import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler)
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from launch.event_handlers import OnShutdown
import os
import xacro

"""
Description:

This launch file is used to start a ROS2 simulation for a Neobotix robot in a specified environment. 
It sets up the Gazebo simulator with the chosen robot and environment, 
optionally starts the robot state publisher, and enables keyboard teleoperation.

You can launch this file using the following terminal commands:

1. `ros2 launch neo_simulation2 simulation.launch.py --show-args`
   This command shows the arguments that can be passed to the launch file.
2. `ros2 launch neo_simulation2 simulation.launch.py my_robot:=mpo_500 world:=neo_track1 arm_type:=ur5e`
   This command launches the simulation with sample values for the arguments.
   !(only mpo_700 and mpo_500 support arms)
"""

# OpaqueFunction is used to perform setup actions during launch through a Python function
def launch_setup(context: LaunchContext, my_neo_robot_arg, my_neo_env_arg, robot_arm_arg, docking_adapter_arg,
                 use_teleop_arg, gui_arg, gui_delay_arg):
    # Create a list to hold all the nodes
    launch_actions = []
    # The perform method of a LaunchConfiguration is called to evaluate its value.
    my_neo_robot = my_neo_robot_arg.perform(context)
    my_neo_environment = my_neo_env_arg.perform(context)
    robot_arm_type = robot_arm_arg.perform(context)
    # "arm_type:=none" means no arm. An empty string cannot be passed from a shell:
    # ros2 launch rejects any argument that ends in ':=' as malformed, so the
    # documented arm_type:="" has never actually worked from the command line.
    if robot_arm_type.strip().lower() in ('', 'none', 'false', '0', 'no'):
        robot_arm_type = ''
    use_docking_adapter = docking_adapter_arg.perform(context)
    use_teleop = use_teleop_arg.perform(context).strip().lower() in ('true', '1', 'yes')
    gui = gui_arg.perform(context).strip().lower() in ('true', '1', 'yes')
    gui_delay = float(gui_delay_arg.perform(context))
    use_sim_time = True

    robots = ["mpo_700", "mp_400", "mp_500", "mpo_500"]

    # Checking if the user has selected a robot that is valid
    if my_neo_robot not in robots:
        # Incase of an invalid selection
        print("Invalid option, setting mpo_700 by default")
        my_neo_robot = "mpo_700"

    # Store the selected robot inside the package share directory rather than the
    # current working directory, so navigation.launch.py / mapping.launch.py find it
    # no matter which directory each launch is started from.
    robot_name_file = os.path.join(
        get_package_share_directory('neo_simulation2'), 'robot_name.txt')

    with open(robot_name_file, 'w') as file:
        file.write(my_neo_robot)

    # Remove arm_type if robot does not support it
    if (robot_arm_type != ''):
        if (my_neo_robot != "mpo_700" and my_neo_robot != "mpo_500"):
            print("Robot does not support arm, setting arm_type to empty")
            robot_arm_type = ''

    # Get the required paths for the world and robot robot_description_urdf
    if my_neo_environment in ("neo_workshop", "neo_track1", "neo_table"):
        world_path = os.path.join(
            get_package_share_directory('neo_simulation2'),
            'worlds',
            my_neo_environment + '.world')
    else:
        world_path = my_neo_environment

    # Gazebo server and client are started SEPARATELY, the client a few seconds
    # later. gazebo_ros's gazebo.launch.py starts both in the same instant, and
    # with a world this size the client's scene request can reach the server
    # before the world is loaded; the reply is then lost and the client sits on
    # an empty scene forever - a blank window, or just the grid when the grid is
    # on. A short delay removes the race.
    gazebo_launch_dir = os.path.join(get_package_share_directory('gazebo_ros'), 'launch')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_launch_dir, 'gzserver.launch.py')),
        launch_arguments={
            'world': world_path,
            'verbose': 'true',
        }.items()
    )
    gazebo_client = TimerAction(
        period=gui_delay,
        actions=[IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gazebo_launch_dir, 'gzclient.launch.py')),
            launch_arguments={'verbose': 'true'}.items())])

    # Getting the robot description xacro
    robot_description_xacro = os.path.join(
        get_package_share_directory('neo_simulation2'),
        'robots/'+my_neo_robot+'/',
        my_neo_robot+'.urdf.xacro')
    
    # Docking adapter is only for MPO 700
    if (my_neo_robot != "mpo_700"):
        use_docking_adapter = False
        
     # use_gazebo is set to True since this code launches the robot in simulation
    xacro_args = {
        'use_gazebo': 'true',
        'arm_type': robot_arm_type,
        'use_docking_adapter': use_docking_adapter
    }

    # Use xacro to process the file with the argunments above
    robot_description_file = xacro.process_file(
        robot_description_xacro, 
        mappings=xacro_args
        ).toxml()

    # Spawning the robot
    spawn_entity = Node(
        package='gazebo_ros', 
        executable='spawn_entity.py',
        arguments=['-entity', my_neo_robot,'-topic', '/robot_description'], 
        output='screen'
    )

    # Start the robot state publisher node
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time, 
                    'robot_description': robot_description_file}]
    )

    # Starting the teleop node
    teleop = Node(
        package='teleop_twist_keyboard',
        executable="teleop_twist_keyboard",
        output='screen',
        prefix = 'xterm -e',
        name='teleop'
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
    )

    initial_joint_controller_spawner_stopped = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "-c", "/controller_manager"],
    )

    # The Robotiq 2F-140 gripper rides along with the UR arm on the same
    # controller_manager, so it needs its own spawner.
    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["robotiq_gripper_controller", "-c", "/controller_manager"],
    )

    # Real-robot topic and action names (neo_mpo_700-2 bringup), so navigation,
    # MoveIt and applications are configured the same way for both targets.
    # The mpo_700 lidars publish lidar_N/scan; these crop them to
    # lidar_N/scan_filtered and merge both into scan in the robot's namespace.
    scan_filters = [
        Node(
            package='neo_simulation2',
            executable='sim_scan_filter.py',
            name='neo_scan_filter_node',
            namespace=lidar,
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}])
        for lidar in ('lidar_1', 'lidar_2')
    ]
    gripper_action_relay = Node(
        package='neo_simulation2',
        executable='gripper_action_relay.py',
        name='gripper_action_relay',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}])

    # See Issue: https://github.com/ros2/rclpy/issues/1287
    # Cannot delete the newly create file. The user has to delete it on his own
    # Refer documentation for more info
    # shutdown_event = RegisterEventHandler(
    #         OnShutdown(
    #             on_shutdown=[os.remove('robot_name.txt')]
    #         )
    #     )

    # The required nodes can just be appended to the launch_actions list
    launch_actions.append(start_robot_state_publisher_cmd)
    if robot_arm_type != '':
        launch_actions.append(joint_state_broadcaster_spawner)
        launch_actions.append(initial_joint_controller_spawner_stopped)
        launch_actions.append(gripper_controller_spawner)
        launch_actions.append(gripper_action_relay)
    if my_neo_robot == 'mpo_700':
        launch_actions.extend(scan_filters)
    launch_actions.append(gazebo)
    if gui:
        launch_actions.append(gazebo_client)
    launch_actions.append(spawn_entity)
    # The teleop xterm rarely receives keyboard focus and is easier to run in
    # your own terminal (ros2 run teleop_twist_keyboard teleop_twist_keyboard),
    # so it is off unless asked for.
    if use_teleop:
        launch_actions.append(teleop)

    # launch_actions.append(shutdown_event)

    return launch_actions

def generate_launch_description():
    ld = LaunchDescription()

    # Declare launch arguments 'my_robot' and 'world' with default values and descriptions
    declare_my_robot_arg = DeclareLaunchArgument(
        'my_robot', 
        default_value='mpo_700',
        description='Robot Types: "mpo_700", "mpo_500", "mp_400", "mp_500"'
    ) 
    
    declare_world_name_arg = DeclareLaunchArgument(
        'world',
        default_value='neo_workshop',
        description='Available worlds: "neo_workshop", "neo_track1", "neo_table" (one big table, no walls - '
                    'do not start navigation there), or a full path to a .world file'
    )

    declare_arm_type_cmd = DeclareLaunchArgument(
        'arm_type', default_value='ur10',
        description='Arm Types:\n'
        '\t Elite Arms: ec66, cs66\n'
        '\t Universal Robotics: ur5, ur10, ur5e, ur10e\n'
        '\t Pass arm_type:=none for a robot with no arm.\n'
        '\t The Robotiq 2F-140 gripper is attached automatically with a UR arm.'
    )

    declare_docking_adapter_cmd = DeclareLaunchArgument(
        'use_docking_adapter', default_value='False',
        description='Set True to use the docking adapter for the robot\n'
        '\t Neobotix: docking_adapter'
    )

    declare_use_teleop_cmd = DeclareLaunchArgument(
        'teleop', default_value='False',
        description='Start teleop_twist_keyboard in an xterm. Off by default: the xterm '
                    'rarely gets keyboard focus; run it in your own terminal instead.'
    )

    declare_gui_cmd = DeclareLaunchArgument(
        'gazebo_gui', default_value='True',
        description='Start the Gazebo window (gzclient). False runs the simulation headless.'
    )

    declare_gui_delay_cmd = DeclareLaunchArgument(
        'gazebo_gui_delay', default_value='6.0',
        description='Seconds after the server before the Gazebo window starts. Started together, '
                    'the window can request the scene before the world is loaded and then shows '
                    'a blank window forever.'
    )

    # Create launch configuration variables for the robot and map name
    my_neo_robot_arg = LaunchConfiguration('my_robot')
    my_neo_env_arg = LaunchConfiguration('world')
    robot_arm_arg = LaunchConfiguration('arm_type')
    docking_adapter_arg = LaunchConfiguration('use_docking_adapter')
    use_teleop_arg = LaunchConfiguration('teleop')
    gui_arg = LaunchConfiguration('gazebo_gui')
    gui_delay_arg = LaunchConfiguration('gazebo_gui_delay')

    ld.add_action(declare_my_robot_arg)
    ld.add_action(declare_world_name_arg)
    ld.add_action(declare_arm_type_cmd)
    ld.add_action(declare_docking_adapter_cmd)
    ld.add_action(declare_use_teleop_cmd)
    ld.add_action(declare_gui_cmd)
    ld.add_action(declare_gui_delay_cmd)

    context_arguments = [my_neo_robot_arg, my_neo_env_arg, robot_arm_arg, docking_adapter_arg,
                         use_teleop_arg, gui_arg, gui_delay_arg]

    opq_function = OpaqueFunction(
        function=launch_setup, 
        args=context_arguments
    )

    ld.add_action(opq_function)

    return ld

