# Neobotix MPO-700 Simulation in Gazebo

This repository contains a ROS 2 Humble simulation of the Neobotix MPO-700 mobile manipulator in Gazebo
Classic 11. The simulated robot carries a UR10 arm and a Robotiq 2F-140 gripper. No physical robot is
required.

The simulation provides:

- autonomous navigation with Nav2
- collision-free arm motion planning with MoveIt 2
- Gazebo services that place objects in the world and attach them to the gripper

The ROS 2 terms used in this documentation are defined in [Terminology](#9-terminology).

## Contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Running the simulation](#3-running-the-simulation)
4. [Launch options](#4-launch-options)
5. [Packages](#5-packages)
6. [System overview](#6-system-overview)
7. [Troubleshooting](#7-troubleshooting)
8. [Known issues](#8-known-issues)
9. [Terminology](#9-terminology)
10. [Further documentation](#10-further-documentation)

---

## 1. Requirements

| Item | Requirement |
| --- | --- |
| Operating system | Ubuntu 22.04 |
| ROS 2 | Humble, desktop installation |
| Simulator | Gazebo Classic 11 (installed in step 2.2) |
| Network | Internet access on the first start: Gazebo downloads several models |

---

## 2. Installation

### 2.1 Install ROS 2 Humble

Install ROS 2 Humble as described in the
[official installation guide](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html).
Install the desktop variant and the development tools:

```bash
sudo apt install ros-humble-desktop ros-dev-tools
```

### 2.2 Install the dependencies

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox \
  ros-humble-moveit ros-humble-ur-description \
  ros-humble-xacro ros-humble-joint-state-publisher-gui ros-humble-teleop-twist-keyboard
```

### 2.3 Create the workspace and clone the repository

```bash
mkdir -p ~/ros2_ws/neobotix_workspace
cd ~/ros2_ws/neobotix_workspace
git clone https://github.com/hsu-aut/Autonomous_systems_simulation.git src
```

### 2.4 Build the workspace

```bash
cd ~/ros2_ws/neobotix_workspace
source /opt/ros/humble/setup.bash
colcon build --symlink-install --allow-overriding robotiq_description \
  --base-paths $(ls -d src/*/ | grep -v mpo_700_workspace)
```

The build is complete when the output ends with `Summary: <n> packages finished`. Compiler warnings do
not indicate a failure.

> **Important:** Always build with this command. The `--base-paths` option excludes
> `src/mpo_700_workspace`, which must not be built in this workspace.

### 2.5 When to rebuild

| Change | Rebuild required |
| --- | --- |
| C++ source files (`.cpp`, `.hpp`) | Yes |
| Files added or deleted | Yes |
| Existing Python, YAML, launch or xacro files | No. `--symlink-install` links these files from `src/`. |

---

## 3. Running the simulation

### 3.1 Prepare each terminal

Run the following commands in every new terminal:

```bash
cd ~/ros2_ws/neobotix_workspace
source /opt/ros/humble/setup.bash
source install/setup.bash
```

### 3.2 Start the simulation

In terminal 1, run:

```bash
ros2 launch neo_simulation2 bringup.launch.py
```

The launch file starts Gazebo, navigation, MoveIt and the monitor window in sequence. This takes
approximately 40 s. Wait until the terminal prints:

```text
You can start planning now!
```

### 3.3 Stop the simulation

In a prepared terminal (step 3.1), run:

```bash
ros2 run neo_simulation2 stop_sim.sh
```

> **Note:** Do not rely on Ctrl-C alone to stop the simulation. Ctrl-C can leave the Gazebo server
> running, and the next start then fails.

> **Note:** If the command reports `port 11345 still held (TIME_WAIT)` and
> `Process exited with failure 1`, all processes are stopped. Wait approximately 30 s before the next
> start.

For error messages and their solutions, see [Troubleshooting](#7-troubleshooting).

---

## 4. Launch options

Pass options to a launch file as `<name>:=<value>` after the file name:

```bash
ros2 launch neo_simulation2 bringup.launch.py use_nav_rviz:=True use_moveit_rviz:=False
```

- Separate multiple options with spaces.
- Boolean options take the values `True` and `False`.
- To list all options of a launch file, append `--show-args`:

  ```bash
  ros2 launch neo_simulation2 bringup.launch.py --show-args
  ```

### 4.1 bringup.launch.py

| Purpose | Options |
| --- | --- |
| Show the navigation map in RViz | `use_nav_rviz:=True` |
| Reduce the CPU load (no MoveIt window) | `use_moveit_rviz:=False` |
| Run without any window | `gui:=False use_moveit_rviz:=False use_monitor:=False` |
| Test grasping at a single table, without navigation | `world:=neo_table use_navigation:=False` |
| Navigation only, without arm | `arm_type:=none use_moveit:=False` |
| Slow computer: start navigation and MoveIt later | `nav_delay:=30 moveit_delay:=40` |

The reference of all launch files and options is in [neo_simulation2/README.md](neo_simulation2/README.md#launch-files).

---

## 5. Packages

Each package contains a `README.md` that describes its function, data flow, files and usage.

| Package | Function | Origin |
| --- | --- | --- |
| **Simulation** | | |
| [neo_simulation2](neo_simulation2/README.md) | Gazebo world, robot description, `bringup.launch.py` | Neobotix, extended |
| [neo_gazebo_plugins](neo_gazebo_plugins/README.md) | Moves the robot base in Gazebo | This project |
| [neo_link_attacher](neo_link_attacher/README.md) | Attaches carried objects to the gripper in Gazebo | This project |
| [neo_sim_objects](neo_sim_objects/README.md) | Places the cube and other objects in Gazebo | This project |
| **Navigation** | | |
| [neo_nav2_bringup](neo_nav2_bringup/README.md) | Starts Nav2 | Neobotix |
| [neo_localization2](neo_localization2/README.md) | Localises the robot on the map | Neobotix |
| [neo_local_planner2](neo_local_planner2/README.md) | Converts the path into velocity commands | Neobotix |
| **Arm and gripper** | | |
| [neo_mpo_moveit2](neo_mpo_moveit2/README.md) | MoveIt configuration for arm motion planning | Neobotix, extended |
| [ros2_robotiq_gripper](ros2_robotiq_gripper/README.md) | 3D model of the gripper | PickNik Robotics |
| **Tools** | | |
| [neo_robot_monitor](neo_robot_monitor/README.md) | Window that displays the robot state | This project |
| **Built, not used by the simulation** | | |
| [neo_msgs2](neo_msgs2/README.md), [neo_srvs2](neo_srvs2/README.md) | Message and service types for Neobotix hardware | Neobotix |
| [serial](serial/README.md) | Serial-port library for the gripper hardware driver | Third-party |

Other items in `src/`:

| Item | Description |
| --- | --- |
| `mpo_700_workspace/` | Software of the physical robot. **Not part of the simulation.** It is the reference for the simulation settings. Do not build it. |

---

## 6. System overview

```text
    ┌────────────────────────────────────────────────────────────────────────┐
    │            Application node  (not part of this repository)             │
    └───────┬───────────────────────────┬─────────────────────────────┬──────┘
            │ /navigate_to_pose         │ /move_action (action)       │ /link_attacher/*
            │ (action)                  │ /compute_ik                 │ /gazebo/get_entity_state
            │                           │ /apply_planning_scene       │ (services)
            │                           │                             │
  ┌─────────▼────────────┐      ┌───────▼────────────────┐            │
  │ Nav2                 │      │ MoveIt                 │            │
  │ neo_nav2_bringup     │      │ move_group             │            │
  │ neo_localization2    │      │ (neo_ur_moveit_config) │            │
  │ neo_local_planner2   │      │                        │            │
  └────┬───────────▲─────┘      └────┬──────────────▲────┘            │
       │ /cmd_vel  │ /scan           │ arm motion   │ /joint_states   │
       │           │ /odom, TF       │ gripper cmd  │                 │
┌──────▼───────────┴─────────────────▼──────────────┴─────────────────▼────────┐
│ Gazebo + simulated robot  (neo_simulation2)                                  │
│ base: neo_planar_move    arm, gripper: ros2_control    2 lidars              │
│ world plugins: neo_link_attacher, gazebo_ros_state                           │
└──────────────────────────────────────────────────────────────────────────────┘

Also:  neo_sim_objects    ──▶ Gazebo   /spawn_entity: places objects, for example a cube
       neo_robot_monitor  ◀── Gazebo   /odom, /joint_states, TF: display only
```

| Component | Function |
| --- | --- |
| Gazebo | Simulates the world and the robot. Publishes odometry, joint states and lidar scans. Executes velocity commands for the base and trajectories for the arm and the gripper. |
| Nav2 | Localises the robot on the map, plans a path and drives the base. |
| MoveIt | Plans collision-free arm motions and sends them to the arm controller. |
| Application node | Not part of this repository. Uses the interfaces shown above: drive goals (Nav2), arm motions (MoveIt), object positions and attachment (Gazebo services). |

---

## 7. Troubleshooting

| Symptom | Cause | Solution |
| --- | --- | --- |
| `colcon build` fails with `Could not find a package configuration file provided by "..."` | A ROS 2 package is not installed | Repeat [installation step 2.2](#22-install-the-dependencies) |
| `Package '...' not found` at launch | The workspace is not sourced in this terminal | Run `source install/setup.bash` |
| `Address already in use`, or Gazebo does not start | A previous Gazebo server is still running | Run `ros2 run neo_simulation2 stop_sim.sh`, then start again |
| The Gazebo window shows no robot and no room | The window started before the world was loaded | Run `gzclient` in another terminal. Do not restart the simulation. |
| The first start pauses for a long time | Gazebo downloads models that are not part of the repository | Wait. Internet access is required once. |
| A node reports that `/compute_ik` or `/move_action` is not available | The node started before MoveIt was ready | Wait for `You can start planning now!`, then start the node again |
| MoveIt goals fail with `MoveIt error -4` and the warning `more than one action server` | MoveIt was started twice | `bringup.launch.py` starts MoveIt. Do not start `neo_ur_moveit.launch.py` in addition. |
| Nav2 reports errors about the `odom` frame | Navigation started before the simulation | Start the simulation first |
| The arm does not move; the controllers do not start | Text in the robot description breaks the controller setup | Run `python3 src/neo_simulation2/scripts/check_urdf_for_ros2_control.py` to locate it |
| The system runs slowly | Too many windows are open | Start with `use_moveit_rviz:=False use_monitor:=False` (see [launch options](#4-launch-options)) |

### Expected log messages

The following messages appear in every run. They do not indicate a fault.

| Message | Explanation |
| --- | --- |
| `No 3D sensor plugin(s) defined for octomap updates`, `Resolution not specified for Octomap` | MoveIt has no depth camera. Objects are added to the planning scene through `/apply_planning_scene` instead. |
| `Parameter 'hold_joints' has already been declared` | The arm and the gripper each have their own controller configuration block. |
| `The root link base_link has an inertia specified in the URDF` | Informational message of the URDF parser. |
| `No goal checker was specified in parameter 'current_goal_checker'` | Nav2 uses its only configured goal checker. |
| `[Deprecated]: "allow_nonzero_velocity_at_trajectory_end"`, `Mapping from 'position' to interface ...` | Informational messages of the arm controllers. |
| RViz `GL_INVALID_VALUE`, `/recognize_objects not available` | Graphics driver message; unused MoveIt RViz feature. |
| After `stop_sim.sh`: `port 11345 still held (TIME_WAIT)`, `[ros2run]: Process exited with failure 1` | All processes are stopped; the network port is released within approximately 30 s. Wait before the next start. |
| After Ctrl-C: `process has died` (RViz, monitor, `move_group`); `failed to terminate ... escalating to 'SIGKILL'` (Nav2) | Normal shutdown. Nav2 takes approximately 15 s to stop. |

---

## 8. Known issues

| Issue | Effect |
| --- | --- |
| `neo_simulation2/launch/mapping.launch.py` passes its parameter file as `params_file`, but the included launch file expects `param_file` | Map building ignores `configs/mpo_700/mapping.yaml` and uses the defaults of `neo_nav2_bringup` (scan topic `/scan`) |
| `use_sim_time` is missing in the `controller_server`, `neo_localization2_node` and `waypoint_follower` sections of `configs/mpo_700/navigation.yaml` | These nodes use the system clock instead of the simulation time |
| The `ur5`, `ur5e` and `ur10e` controller files define no `robotiq_gripper_controller` | With `arm_type` other than `ur10`, the gripper controller does not start |

---

## 9. Terminology

| Term | Definition |
| --- | --- |
| Workspace | The build folder, `~/ros2_ws/neobotix_workspace`. The source code is in its `src/` folder. |
| Package | A folder with a `package.xml` file; the unit that ROS 2 builds and installs. |
| Build | Compilation of the packages with `colcon build`. The result is written to `install/`. |
| Source | `source install/setup.bash` makes the built packages available in the current terminal. Required in every new terminal. |
| Node | A running ROS 2 program, for example `move_group`. |
| Topic | A named message stream, for example `/odom` (base position and velocity) or `/cmd_vel` (velocity commands). |
| Service | A request with an immediate response, for example the position of an object in Gazebo. |
| Action | A long-running request with feedback and a final result, for example driving to a pose or closing the gripper. |
| Launch file | A Python file that starts several nodes with their parameters: `ros2 launch <package> <file> [<name>:=<value> ...]`. |
| URDF, xacro | The robot description: its parts (links) and the joints between them. Xacro is URDF with macros. |
| Frame, TF | A coordinate system, for example `map` (the room), `base_link` (the robot base) or `grasp_tcp` (between the gripper fingers). TF maintains the transforms between all frames. |
| Gazebo | The physics simulator: world, robot, gravity, collisions. |
| Nav2 | The ROS 2 navigation stack: localisation on a map, path planning, driving. |
| MoveIt | The arm motion-planning framework: collision-free arm motions. |
| Controller | A ros2_control component that moves joints, for example `joint_trajectory_controller` for the arm. |
| Simulation time | The Gazebo clock. Nodes started with `use_sim_time:=True` use it instead of the system clock. |

### Useful commands

Run these commands in a prepared terminal while the simulation is running.

| Command | Output |
| --- | --- |
| `ros2 node list` | Running nodes |
| `ros2 topic list` | Available topics |
| `ros2 topic echo /odom` | Messages on a topic; stop with Ctrl-C |
| `ros2 service list` | Available services |
| `ros2 action list` | Available actions |

---

## 10. Further documentation

| Document | Content |
| --- | --- |
| [neo_simulation2/README.md](neo_simulation2/README.md#launch-files) | All launch files of the simulation and their options |
| [neo_simulation2/README.md](neo_simulation2/README.md#comparison-with-the-physical-robot) | Origin of the settings and differences from the physical robot |
| [ros2_robotiq_gripper/GRIPPER_INTEGRATION.md](ros2_robotiq_gripper/GRIPPER_INTEGRATION.md) | Development report: integration of the gripper into the simulation (background information) |
