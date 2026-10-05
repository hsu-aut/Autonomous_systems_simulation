# Terminology

Short explanations of the ROS 2 and robotics terms used in this documentation, with examples from this
simulation. At the end you find commands for looking into the running simulation.

## Contents

1. [Workspace and build](#1-workspace-and-build)
2. [ROS 2 programs and communication](#2-ros-2-programs-and-communication)
3. [Robot description and coordinates](#3-robot-description-and-coordinates)
4. [Simulation, navigation and arm](#4-simulation-navigation-and-arm)
5. [Useful commands](#5-useful-commands)

---

## 1. Workspace and build

| Term | Explanation |
| --- | --- |
| Workspace | The folder in which the software is built: `neobotix_workspace` in the home folder. The source code (this repository) is its subfolder `src/`. |
| Package | A folder with a `package.xml` file; the unit that ROS 2 builds and installs. Example: `neo_simulation2`. |
| Build | Compiling the packages with `colcon build`. The result is written to the folder `install/`. |
| Source | `source install/setup.bash` makes the built packages available in the current terminal. `.bashrc` does this in every new terminal ([installation step 6](Installation.md#6-set-up-the-terminal)). |

## 2. ROS 2 programs and communication

| Term | Explanation |
| --- | --- |
| Node | A running ROS 2 program. Example: `move_group`, the main program of MoveIt. |
| Topic | A named stream of messages: one node publishes, any number of nodes listen. Examples: `/odom` (position and velocity of the base), `/cmd_vel` (velocity commands for the base). |
| Service | A request with an immediate answer. Example: asking Gazebo for the position of an object. |
| Action | A longer task with feedback while it runs and a result at the end. Examples: driving to a position, closing the gripper. |
| Launch file | A Python file that starts several nodes with their settings at once: `ros2 launch <package> <file>`. |
| Launch argument | A setting passed to a launch file as `<name>:=<value>`. Example: `moveit:=True`. See [Launch_arguments.md](Launch_arguments.md). |
| Middleware (DDS) | The layer that carries the messages between the nodes. The simulation uses Cyclone DDS ([installation step 7](Installation.md#7-configure-the-ros-2-middleware)). |
| Domain ID | A number (`ROS_DOMAIN_ID`, here 73). Only nodes with the same domain ID see each other. |

## 3. Robot description and coordinates

| Term | Explanation |
| --- | --- |
| URDF, xacro | The robot description: its parts (links) and the joints between them. Xacro is URDF with macros. |
| Frame | A coordinate system. Examples: `map` (the room), `odom` (the start point of the odometry), `base_link` (the robot base), `grasp_tcp` (the point between the gripper fingers). |
| TF | The ROS 2 system that knows how all frames are positioned relative to each other, for example where `base_link` is in `map`. |
| Odometry | The position of the robot, calculated from its wheel motion. It drifts slowly over time; localisation corrects it with the lidar scans. |
| Lidar | A laser scanner that measures the distance to the surroundings in a plane. The MPO-700 has two. |
| Yaw | The heading of the robot: its rotation about the vertical axis. 0° faces along the x axis of the map. |
| Quaternion | The way ROS 2 writes orientations: four numbers (x, y, z, w). For a pure yaw rotation: x = 0, y = 0, z = sin(yaw / 2), w = cos(yaw / 2). |

## 4. Simulation, navigation and arm

| Term | Explanation |
| --- | --- |
| Gazebo | The physics simulator: world, robot, gravity, collisions. |
| RViz | The visualisation tool of ROS 2. It shows what the robot knows (map, laser scans, planned paths, arm motions), and you give goals there. |
| Simulation time | The clock of Gazebo. Nodes started with `use_sim_time:=True` use it instead of the computer clock. |
| Controller | A ros2_control component that moves joints. Example: `joint_trajectory_controller` moves the arm. |
| Teleoperation | Driving the robot by hand. Here: with the keyboard, using `teleop_twist_keyboard`. |
| Nav2 | The ROS 2 navigation software: it localises the robot on the map, plans a path and drives the robot along it. |
| Map | A floor plan of a world, used by navigation: free space and obstacles. Stored in `neo_simulation2/maps/`. |
| Localisation | Determining where the robot is on the map, by comparing the lidar scans with the map. |
| MoveIt | The software that plans collision-free arm motions and executes them. |
| Planning group | The joints that MoveIt plans for together. Here: `ur_manipulator` (the arm) and `gripper`. |
| Named state | An arm or gripper pose stored under a name, for example `home` or `open`. In RViz: **Goal State**. |

## 5. Useful commands

Run these commands in a second terminal while the simulation is running.

| Command | Shows |
| --- | --- |
| `ros2 node list` | All running nodes |
| `ros2 node info /move_group` | The topics, services and actions of one node |
| `ros2 topic list` | All topics |
| `ros2 topic echo /odom` | The messages on a topic as they arrive; stop with Ctrl-C. Add `--once` for a single message. |
| `ros2 topic info /cmd_vel` | How many nodes publish and listen on a topic |
| `ros2 service list` | All services |
| `ros2 action list` | All actions |
| `ros2 control list_controllers` | The controllers and whether they are active |
| `ros2 launch neo_simulation2 bringup.launch.py --show-args` | All launch arguments of the simulation (no simulation needs to be running) |
