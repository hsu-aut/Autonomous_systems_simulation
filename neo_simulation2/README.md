# neo_simulation2

This package provides the Gazebo simulation of the MPO-700: world files, robot description, controller
configuration, helper nodes, and `bringup.launch.py`, which starts the complete system.

| Property | Value |
| --- | --- |
| Origin | Neobotix; extended for this project (UR10 arm, Robotiq 2F-140 gripper, settings of the physical robot, see [Comparison with the physical robot](#comparison-with-the-physical-robot)) |
| Type | Launch files, robot description, configuration, helper nodes (Python) |
| Start command | `ros2 launch neo_simulation2 bringup.launch.py` |
| Options | [Launch files](#launch-files) |

Contents:

1. [Start-up sequence](#start-up-sequence)
2. [Data flow](#data-flow)
3. [Files](#files)
4. [Helper nodes](#helper-nodes)
5. [Robot description](#robot-description)
6. [Worlds](#worlds)
7. [Launch files](#launch-files)
8. [Comparison with the physical robot](#comparison-with-the-physical-robot)
9. [Gazebo Classic](#gazebo-classic)

## Start-up sequence

`bringup.launch.py` starts the components in the following order. Navigation and MoveIt require the
simulated robot to be running.

```text
  0 s ─┬─ simulation.launch.py   Gazebo, robot, controllers, helper nodes
       │
 20 s ─┼─ navigation.launch.py   map, localisation, Nav2
       │
 26 s ─┼─ MoveIt                 move_group and the MoveIt window
       │
 32 s ─┼─ navigation window      only with use_nav_rviz:=True
       │
 36 s ─┴─ monitor window         neo_robot_monitor
```

## Data flow

```text
/cmd_vel                arm trajectory        gripper command (action, MoveIt)
(Nav2, teleop)          (action, MoveIt)      /robotiq_gripper/
    │                       │                 robotiq_gripper_controller/gripper_cmd
    │                       │                         │
    │                       │                 ┌───────▼──────────────┐
    │                       │                 │ gripper_action_relay │
    │                       │                 └───────┬──────────────┘
    │                       │                         │ /robotiq_gripper_controller/
    │                       │                         │ gripper_cmd
┌───▼───────────────────────▼─────────────────────────▼──────────────────────────┐
│ Gazebo (gzserver)                                                              │
│   neo_planar_move       moves the base                                         │
│   gazebo_ros2_control   joint_trajectory_controller   (arm)                    │
│                         robotiq_gripper_controller    (gripper)                │
│                         joint_state_broadcaster                                │
│   2 lidar sensors                                                              │
└───┬─────────────────────────┬─────────────────────────────────┬────────────────┘
    │ /odom                   │ /joint_states                   │ lidar_1/scan, lidar_2/scan
    │ TF odom → base_link     │                                 │
    │                         │                                 │
    ▼                 ┌───────▼───────────────┐           ┌─────▼────────────────┐
Nav2, applications    │ robot_state_publisher │ ────▶ TF  │ sim_scan_filter (×2) │
                      └───────────────────────┘           └───┬───────────────┬──┘
                                                              │               │
                                                              ▼               ▼
                                                    lidar_N/scan_filtered   /scan
                                                         (costmaps)    (localisation)
```

## Files

```text
neo_simulation2/
├── launch/
│   ├── bringup.launch.py              complete system (standard start)
│   ├── simulation.launch.py           Gazebo, robot, controllers, helper nodes
│   ├── navigation.launch.py           map, localisation, Nav2 (includes neo_nav2_bringup)
│   ├── mapping.launch.py              map building (slam_toolbox)
│   └── robot_description.launch.py    robot model in RViz, without Gazebo
├── robots/mpo_700/                    robot description: mpo_700.urdf.xacro and its parts
├── components/
│   ├── arm/                           UR arm and Robotiq gripper, including the grasp frames
│   │                                  grasp_tcp, grasp_tip and gripper_tcp
│   └── common_macro/                  lidar sensors, base plugin, shared macros
├── configs/
│   ├── mpo_700/                       navigation.yaml, mapping.yaml, behavior_trees/
│   │                                  (copies of the files of the physical robot)
│   └── ur_config/ur10/                ur_controllers.yaml: arm and gripper controllers
├── worlds/                            neo_workshop (default), neo_table, neo_track1, neo_track2
├── maps/                              navigation maps, one per world
├── models/                            Gazebo models used by the worlds
├── rviz/                              RViz configurations
└── scripts/                           helper nodes, stop script, URDF check (see "Helper nodes")
```

## Helper nodes

The helper nodes in `scripts/` adapt the Gazebo interfaces to the topic and action names that Nav2
and MoveIt use. `bringup.launch.py` starts them.

| File | Function |
| --- | --- |
| `sim_scan_filter.py` | Limits each lidar scan to ±130° (`lidar_N/scan` → `lidar_N/scan_filtered`) and merges both lidars into `/scan` |
| `gripper_action_relay.py` | Provides the gripper action under the name used by MoveIt, and forwards each goal to the gripper controller |
| `stop_sim.sh` | Not a node. Stops the simulation cleanly: `ros2 run neo_simulation2 stop_sim.sh` |
| `check_urdf_for_ros2_control.py` | Not a node. Run it after editing the robot description: it reports text that prevents the controllers from starting. |

## Robot description

- Main file: `robots/mpo_700/mpo_700.urdf.xacro` (base with two lidars, cabinet, UR10 arm, gripper).
- Arm joint and link names carry the prefix `ur10`, for example `ur10shoulder_pan_joint` and
  `ur10tool0`.
- Gazebo plugins: `gazebo_ros2_control` (arm and gripper), two lidar sensors, `neo_planar_move` (base,
  package `neo_gazebo_plugins`).

Controllers (`configs/ur_config/ur10/ur_controllers.yaml`):

| Controller | Function |
| --- | --- |
| `joint_state_broadcaster` | Publishes all joint angles on `/joint_states` |
| `joint_trajectory_controller` | Moves the arm; MoveIt sends its trajectories here |
| `robotiq_gripper_controller` | Moves the gripper (`finger_joint`) |

## Worlds

| World (`world:=`) | Content | Map (`map:=`) |
| --- | --- | --- |
| `neo_workshop` (default) | Workshop with two tables | `neo_workshop` |
| `neo_table` | One table with a cube; robot parked in front of it | None; set `use_navigation:=False` |
| `neo_track1`, `neo_track2` | Driving tracks | `neo_track1`, `neo_track2` |

`neo_workshop` and `neo_table` load two Gazebo world plugins: `gazebo_ros_state` (positions of all
objects) and `neo_link_attacher` (carrying the cube).

## Launch files

General usage:

- Run all commands in a prepared terminal (see [main README, step 3.1](../README.md#31-prepare-each-terminal)).
- Pass options as `<name>:=<value>` after the file name. Separate multiple options with spaces.
- To list all options of a launch file, append `--show-args`.

| Launch file | Starts | Use |
| --- | --- | --- |
| [bringup.launch.py](#bringuplaunchpy) | Gazebo, robot, navigation, MoveIt, windows | Standard start of the simulation |
| [simulation.launch.py](#simulationlaunchpy) | Gazebo and robot | Simulation without navigation and MoveIt |
| [navigation.launch.py](#navigationlaunchpy) | Navigation | Adds navigation to a running simulation |
| [mapping.launch.py](#mappinglaunchpy) | Map building | Creates a map of a new world |
| [robot_description.launch.py](#robot_descriptionlaunchpy) | Robot model in RViz, without Gazebo | Inspection of the robot model |

Launch files of other packages:

| Launch file | Package | Reference |
| --- | --- | --- |
| `spawn_objects.launch.py` | `neo_sim_objects` | [Usage](../neo_sim_objects/README.md#usage) |
| `monitor.launch.py` | `neo_robot_monitor` | [Standalone start](../neo_robot_monitor/README.md#standalone-start) |
| `neo_ur_moveit.launch.py` | `neo_ur_moveit_config` | [Standalone start](../neo_mpo_moveit2/README.md#standalone-start) |

### bringup.launch.py

```bash
ros2 launch neo_simulation2 bringup.launch.py
```

The components start in the order shown in [Start-up sequence](#start-up-sequence). Wait until the
terminal prints `You can start planning now!` before sending goals to MoveIt.

| Option | Default | Description |
| --- | --- | --- |
| `world` | `neo_workshop` | World: `neo_workshop`, `neo_table` (one table with a cube), `neo_track1`, `neo_track2`, or the full path of a `.world` file |
| `map` | `neo_workshop` | Navigation map: `neo_workshop`, `neo_track1`, `neo_track2`, or the full path of a `.yaml` file. Set it together with `world`. |
| `use_navigation` | `True` | Start navigation |
| `use_moveit` | `True` | Start MoveIt |
| `arm_type` | `ur10` | Arm type. `none` removes the arm; then also set `use_moveit:=False`. |
| `gui` | `True` | Open the Gazebo window |
| `use_moveit_rviz` | `True` | Open the MoveIt RViz window. `False` reduces the CPU load considerably. |
| `use_nav_rviz` | `False` | Open the navigation RViz window |
| `use_monitor` | `True` | Open the monitor window |
| `tcp_frame` | `ur10tool0` | Gripper frame shown in the monitor; `grasp_tcp` is the point between the fingers |
| `use_amcl` | `False` | Use Nav2 AMCL instead of `neo_localization2` for localisation |
| `nav_delay`, `moveit_delay`, `rviz_delay`, `monitor_delay` | `20`, `26`, `32`, `36` | Start delays in seconds; increase them on a slow computer |
| `use_teleop` | `False` | Open a keyboard teleoperation window |

> **Note:** `--show-args` lists approximately 30 options. Options not listed above are forwarded to the
> included launch files; keep their default values.

> **Note:** The project is configured for `my_robot:=mpo_700` with `arm_type:=ur10` (the defaults). The
> other robot and arm types originate from Neobotix and are not configured for this project. The `ur5`,
> `ur5e` and `ur10e` configurations have no gripper controller.

Examples:

```bash
# Show the navigation map; do not open the MoveIt window
ros2 launch neo_simulation2 bringup.launch.py use_nav_rviz:=True use_moveit_rviz:=False

# Run without any window
ros2 launch neo_simulation2 bringup.launch.py gui:=False use_moveit_rviz:=False use_monitor:=False

# Test grasping at a single table, without navigation
ros2 launch neo_simulation2 bringup.launch.py world:=neo_table use_navigation:=False

# Navigation only, on a driving track, without arm and MoveIt
ros2 launch neo_simulation2 bringup.launch.py world:=neo_track1 map:=neo_track1 arm_type:=none use_moveit:=False
```

### simulation.launch.py

```bash
ros2 launch neo_simulation2 simulation.launch.py
```

- Starts Gazebo, the robot and its controllers, without navigation and MoveIt.
- Options: `world`, `arm_type`, `gui` (as for `bringup.launch.py`).

To drive the robot with the keyboard, run in a second terminal:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### navigation.launch.py

Prerequisite: the simulation is running.

```bash
ros2 launch neo_simulation2 navigation.launch.py map:=neo_workshop
```

- Options: `map`, `use_amcl` (as for `bringup.launch.py`).
- Parameters: `configs/mpo_700/navigation.yaml`.

### mapping.launch.py

1. Start the world to be mapped (terminal 1):

   ```bash
   ros2 launch neo_simulation2 simulation.launch.py world:=<world>
   ```

2. Start map building (terminal 2):

   ```bash
   ros2 launch neo_simulation2 mapping.launch.py use_sim_time:=True
   ```

3. Drive the robot through the whole world (terminal 3):

   ```bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard
   ```

4. Save the map (terminal 4):

   ```bash
   ros2 run nav2_map_server map_saver_cli -f src/neo_simulation2/maps/<name>
   ```

After saving, the option `map:=<name>` is available in `bringup.launch.py` and `navigation.launch.py`.

> **Note:** Always set `use_sim_time:=True` for this launch file; its default is `False`. See also the
> [known issue](../README.md#8-known-issues) about its parameter file.

### robot_description.launch.py

```bash
ros2 launch neo_simulation2 robot_description.launch.py
```

Displays the robot model in RViz, with a slider for each joint. Gazebo is not started.

## Comparison with the physical robot

The simulation uses the names and settings of the physical MPO-700, so that it behaves like the
physical robot. This section describes the origin of the settings and the remaining differences. It is
background information; it is not required to use the simulation.

The software of the physical robot is located in `src/mpo_700_workspace` (on the robot PC:
`~/mpo_700_workspace`). This folder is not part of the simulation. Do not edit or build it.

### Identical settings

| Item | Value in simulation and on the physical robot |
| --- | --- |
| Joint and link names | Identical. Every link of the physical robot model exists in the simulation with the same name and position. Arm names carry the prefix `ur10`. |
| Lidar topics | `lidar_1/scan`, `lidar_2/scan` (raw); `lidar_1/scan_filtered`, `lidar_2/scan_filtered` (limited to ±130°); `/scan` (both lidars) |
| Lidar coverage | 270°, one reading every 0.5° |
| Navigation parameters | `configs/mpo_700/navigation.yaml`, the behavior trees and `mapping.yaml` are copies of the files of the physical robot |
| Command timeout of the base | The base stops when no velocity command arrives for 0.2 s |
| Gripper action | `/robotiq_gripper/robotiq_gripper_controller/gripper_cmd` |
| MoveIt controller configuration | `neo_ur_moveit_config/config/controllers.yaml` is identical |

Use of the lidar topics:

| Consumer | Topic |
| --- | --- |
| Localisation (`neo_localization2`) | `/scan` |
| Navigation costmaps | `lidar_1/scan_filtered` and `lidar_2/scan_filtered`, as separate sources |
| Map building (`slam_toolbox`) | Physical robot: `lidar_1/scan_filtered`. Simulation: currently `/scan` (see [known issues](../README.md#8-known-issues)). |

### Differences

| Item | Simulation | Physical robot | Reason |
| --- | --- | --- | --- |
| Arm controller | `joint_trajectory_controller` | `scaled_joint_trajectory_controller` | The scaled controller requires a speed-scaling signal that only the physical arm provides |
| Arm path tolerance | 1.0 rad | 0.2 rad | With 0.2 rad, Gazebo aborted long arm motions |
| Controller update rate | 100 Hz | 125 Hz | Gazebo advances in steps of 0.01 s; 100 Hz is the maximum |
| Lidar rate | 20 Hz | 25 Hz | Reduced CPU load |
| Base motion | Exactly at the commanded velocity | Wheels first steer to the commanded direction | Wheel steering is not modelled in Gazebo |
| Gripper stalling on an object | Allowed (`allow_stalling: true`) | Controller default | The simulated fingers cannot exert force on the cube |
| Gripper action name | Provided by `gripper_action_relay.py` | Provided by the driver | See [Helper nodes](#helper-nodes) |
| Lidar limiting and merging | `sim_scan_filter.py` | `neo_scan_filter_node` and `topic_tools relay` | The packages of the physical robot are not part of this workspace |
| MoveIt planners | OMPL and Pilz | OMPL | Pilz provides straight-line motions for grasping |
| Grasp frames | `grasp_tcp`, `grasp_tip`, `gripper_tcp` | `gripper_tcp` | Exact finger centre and fingertip for grasp planning |
| Clock | Simulation time | System clock | |

### Source of the settings

| Setting | File in `src/mpo_700_workspace/src/` |
| --- | --- |
| Robot model | `neo_mpo_700-2/robot_model/mpo_700/mpo_700.urdf.xacro` |
| Navigation | `neo_mpo_700-2/configs/navigation/` |
| Base (wheels, timeout) | `neo_mpo_700-2/configs/kinematics/kinematics.yaml` |
| Lidars | `neo_mpo_700-2/configs/lidar/sick/s300/` |
| Gripper | `neo_mpo_700-2/configs/robotiq/robotiq_control.launch.py` |
| Arm driver | `neo_mpo_700-2/configs/ur/ur_control.launch.py` |
| Operating instructions of the physical robot | `README.md` |

To adopt a further setting of the physical robot, change the simulation file, not the file of the
physical robot. If the value cannot work in Gazebo, add a row to [Differences](#differences).

> **Important:** Do not add a `COLCON_IGNORE` file to `src/mpo_700_workspace`. That file also prevents
> the workspace from building when it is copied to the robot PC. Exclude it with the
> [build command](../README.md#24-build-the-workspace) instead.

## Gazebo Classic

- Neobotix documentation: <https://neobotix-docs.de/ros/ros2/simulation_classic.html>
- Gazebo Classic has reached end of life. Neobotix no longer maintains this package and has moved its
  robots to [modern Gazebo](https://neobotix-docs.de/ros/ros2/simulation_modern.html). This project
  continues to use Gazebo Classic 11.
