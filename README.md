# Neobotix MPO-700 Simulation in Gazebo

This repository contains a simulation of the Neobotix MPO-700, a mobile robot with an arm. The robot
can drive in any direction, also sideways, and carries a UR10 arm with a Robotiq 2F-140 gripper. The
simulation runs with ROS 2 Humble in Gazebo Classic 11 on your own computer; no physical robot is
needed.

With the simulation you can:

- drive the robot with the keyboard,
- let the robot drive to a goal on its own (navigation with Nav2),
- plan and execute collision-free arm and gripper motions (MoveIt 2),
- write your own program that picks up a cube and places it on another table: the simulation places
  objects in the world and attaches them to the gripper on request.

## Quick start

1. Install the simulation once: [Installation.md](Installation.md).
2. Start the simulation, for example with all components:
   `ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True moveit_rviz:=True`
   (the other start options are in [section 1.2](#12-start-the-simulation)).
3. Stop the simulation: `ros2 run neo_simulation2 stop_sim.sh`

## Where to find what

| You want to ... | Read |
| --- | --- |
| install the simulation | [Installation.md](Installation.md) |
| start, use and stop the simulation | [Running the simulation](#1-running-the-simulation), below |
| choose what starts (world, windows, components) and learn how to use each start option | [Launch_arguments.md](Launch_arguments.md) |
| solve an error | [Troubleshooting.md](Troubleshooting.md) |
| look up a ROS 2 term or command | [Terminology.md](Terminology.md) |
| program the pick-and-place mission | [Stage_values.md](Stage_values.md) |
| understand or change a package | its `README.md`, see [Packages](#2-packages) |
| look up launch files, worlds, the start-up sequence or the differences to the physical robot | [neo_simulation2/README.md](neo_simulation2/README.md) |
| read how the gripper was integrated (background) | [ros2_robotiq_gripper/GRIPPER_INTEGRATION.md](ros2_robotiq_gripper/GRIPPER_INTEGRATION.md) |

## Contents

1. [Running the simulation](#1-running-the-simulation)
2. [Packages](#2-packages)
3. [System overview](#3-system-overview)

---

## 1. Running the simulation

Run all commands in the workspace folder `neobotix_workspace` (see
[Installation.md](Installation.md#4-create-the-workspace-and-clone-the-repository)).

The robot has three parts that you move separately:

| Part | What it is | Moved by | Section |
| --- | --- | --- | --- |
| Mobile platform | The base with the wheels; it carries the arm | Keyboard or navigation (Nav2) | [1.3](#13-mobile-platform-drive-with-the-keyboard-optional), [1.4](#14-mobile-platform-drive-autonomously-to-the-pick-place-and-home-positions) |
| Manipulator arm | The UR10 arm on top of the platform | MoveIt | [1.5](#15-manipulator-arm-move-to-the-mission-poses) |
| Gripper | The Robotiq 2F-140 at the end of the arm | Gripper action | [1.6](#16-gripper-open-and-close), [1.7](#17-gripper-attach-and-detach-the-cube) |

Each command moves only its own part. A navigation goal drives the platform and leaves the arm in its
pose; an arm goal moves the arm, and the platform stays where it is.

### 1.1 Prepare a terminal

After the installation, every new terminal is ready to use. To check a terminal, run:

```bash
echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID    # prints: rmw_cyclonedds_cpp 73
```

If it prints nothing, the terminal was opened before the installation was finished
([installation steps 6 and 7](Installation.md#6-set-up-the-terminal)): run
`source ~/.bashrc`, or open a new terminal.

### 1.2 Start the simulation

There are four start options. Choose the one that fits what you want to do:

| Option | Use it to ... | Windows that open |
| --- | --- | --- |
| 1. Gazebo only | drive the robot yourself with the keyboard | Gazebo, keyboard window |
| 2. Gazebo + Navigation | let the robot drive to goals on its own | Gazebo, navigation RViz |
| 3. Gazebo + MoveIt | move the arm and the gripper | Gazebo, MoveIt RViz |
| 4. Gazebo + Navigation + MoveIt | do both, for example the pick-and-place mission | Gazebo, navigation RViz, MoveIt RViz |

Gazebo shows the simulated world with the robot. RViz shows what the robot knows (map, laser scans,
planned paths and arm motions), and you give it goals there.

In a terminal, run the command of your option:

**1. Gazebo only**, driving with the keyboard:

```bash
ros2 launch neo_simulation2 bringup.launch.py teleop:=True
```

**2. Gazebo + Navigation**:

```bash
ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True
```

**3. Gazebo + MoveIt** (arm and gripper):

```bash
ros2 launch neo_simulation2 bringup.launch.py moveit_rviz:=True
```

**4. Gazebo + Navigation + MoveIt**:

```bash
ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True moveit_rviz:=True
```

Everything except Gazebo is off by default. `navigation_rviz:=True` and `moveit_rviz:=True` start
navigation and MoveIt together with their RViz windows. To start them without a window, for example
when your own program sends the goals, use `navigation:=True` or `moveit:=True` instead.

| Argument | Default | `True` starts |
| --- | :---: | --- |
| `navigation` | `False` | Navigation, without its RViz window |
| `navigation_rviz` | `False` | Navigation **and** its RViz window |
| `moveit` | `False` | MoveIt, without its RViz window |
| `moveit_rviz` | `False` | MoveIt **and** its RViz window |

For example, MoveIt only, without its window:

```bash
ros2 launch neo_simulation2 bringup.launch.py moveit:=True
```

How the switches combine (for example, both `moveit` and `moveit_rviz` set to `True`) is described in
[Launch_arguments.md](Launch_arguments.md#25-navigation-moveit-and-their-rviz-windows).

The components start one after the other: the Gazebo window after about 6 s, navigation after 20 s,
MoveIt after 26 s. The start is complete after about 40 s; wait until then before you send goals. The
exact order is shown in the [start-up sequence](neo_simulation2/README.md#start-up-sequence).

How to drive with the keyboard, send navigation goals and move the arm in each option is described in
[Launch_arguments.md](Launch_arguments.md#2-start-options).

**Choosing a world.** The robot starts in `neo_workshop`. For another world, add `world:=<name>` to the
command; with navigation (options 2 and 4), also add `map:=<name>`, so that navigation uses the map
of that world.

| World | Content | Map |
| --- | --- | --- |
| `neo_workshop` (default) | Workshop with two tables; the cube is placed on the first table | `neo_workshop` (default) |
| `neo_table` | One table with a cube; the robot is parked in front of it | None; use option 1 or 3 |
| `neo_track1` | Driving track with barriers | `neo_track1` |

For example, option 2 on the driving track:

```bash
ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True world:=neo_track1 map:=neo_track1
```

### 1.3 Mobile platform: drive with the keyboard (Optional)

Without navigation (options 1 and 3), you can drive the mobile platform yourself. In a second
terminal, run:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Option 1 already starts it for you (`teleop:=True`), in a separate window. Keep the terminal or window
with `teleop_twist_keyboard` active, and hold a key down; the robot stops 0.2 s after the last key
press.

| Key | Motion |
| --- | --- |
| `i` / `,` | Forward / backward |
| `j` / `l` | Turn left / right |
| `J` / `L` (with Shift) | Move sideways to the left / right |
| `k` | Stop |
| `q` / `z` | Increase / decrease the speed by 10 % |

> **Note:** Do not drive with the keyboard while navigation is running (options 2 and 4): Nav2 sends
> its own drive commands, and the two would conflict.

### 1.4 Mobile platform: drive autonomously to the pick, place and home positions

These commands drive the **mobile platform** to the positions of the pick-and-place mission
([Stage_values.md](Stage_values.md#2-robot-positions)). Only the platform moves; the arm keeps its
current pose. To move the arm, see [section 1.5](#15-manipulator-arm-move-to-the-mission-poses).

1. Start the simulation with navigation in `neo_workshop` (option 2 or 4).
2. Make sure the arm is in its `home` pose, the travel pose: folded above the platform. The simulation
   starts with the arm in this pose. If you have moved the arm (option 4), move it back to `home` first
   ([section 1.5](#15-manipulator-arm-move-to-the-mission-poses)); in the mission, this is stage S1.
3. In a second terminal, run the command of the position.

**Pick position**, in front of the pick table (stage S2; x -1.51 m, y -3.58 m, yaw -90°):

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -1.51, y: -3.58}, orientation: {z: -0.7071, w: 0.7071}}}}"
```

**Place position**, in front of the place table (stage S6; x -4.65 m, y -3.56 m, yaw -90°):

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -4.65, y: -3.56}, orientation: {z: -0.7071, w: 0.7071}}}}"
```

**Home position**, back at the start (stage S10; x -0.02 m, y 0.00 m, yaw 0°):

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -0.02, y: 0.0}, orientation: {z: 0.0, w: 1.0}}}}"
```

The command ends when the platform has reached the goal; Ctrl-C cancels the goal, and the platform
stops. How to send the platform to other positions is described in
[neo_nav2_bringup/README.md](neo_nav2_bringup/README.md#from-a-terminal). You can also send goals
in the navigation RViz window with **Nav2 Goal**
([Launch_arguments.md](Launch_arguments.md#22-option-2-navigation-goals)).

> **Note:** *Home* means two different things: the **home position** of the platform on the map (this
> section) and the **`home` pose** of the arm, its travel pose ([section 1.5](#15-manipulator-arm-move-to-the-mission-poses)).
> Each is set with its own command.

### 1.5 Manipulator arm: move to the mission poses

These steps move the **manipulator arm** (the UR10) into the poses of the pick-and-place mission
([Stage_values.md](Stage_values.md#3-arm-poses)). Only the arm moves; the platform stays where it is.
To move the platform, see [section 1.3](#13-mobile-platform-drive-with-the-keyboard-optional) and
[section 1.4](#14-mobile-platform-drive-autonomously-to-the-pick-place-and-home-positions).

The arm needs only three poses, stored in MoveIt as named states of the planning group
`ur_manipulator`:

| Named state | Pose of the arm | Platform at |
| --- | --- | --- |
| `home` | Travel pose: arm folded above the platform | Any position |
| `pregrasp` | Gripper 16 cm above the cube or the place point | Pick or place position |
| `grasp` | Gripper at the cube or the place point | Pick or place position |

`pregrasp` and `grasp` reach over a table. They are used at both tables: at the place table, the same
two poses put the cube down. They fit only when the platform is at the pick or place position
([section 1.4](#14-mobile-platform-drive-autonomously-to-the-pick-place-and-home-positions)).

At each table, the arm moves `pregrasp` → `grasp` → `pregrasp`, and the gripper works in between:

| Step | At the pick table | At the place table |
| --- | --- | --- |
| 1 | `pregrasp`, gripper open | `pregrasp`, holding the cube |
| 2 | `grasp` | `grasp` |
| 3 | Close the gripper, attach the cube | Detach the cube, open the gripper |
| 4 | `pregrasp`: the cube is lifted | `pregrasp`: the gripper moves away from the cube |

The gripper commands of step 3 are in [section 1.6](#16-gripper-open-and-close) and
[section 1.7](#17-gripper-attach-and-detach-the-cube).

To move the arm, start the simulation with the MoveIt RViz window (option 3 or 4), and in RViz:

1. In the **MotionPlanning** panel, select the planning group `ur_manipulator`.
2. Under **Goal State**, select the named state, for example `home`.
3. Click **Plan & Execute**.

MoveIt plans a path that avoids collisions of the robot with itself. The tables are not part of
MoveIt's planning scene unless your own program adds them. In your own program, use the named states
as named targets; see [Stage_values.md](Stage_values.md#4-using-the-values-in-a-moveit-client).

The gripper is moved separately ([section 1.6](#16-gripper-open-and-close)).

### 1.6 Gripper: open and close

In a second terminal:

**Open**:

```bash
ros2 action send_goal /robotiq_gripper/robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.07, max_effort: 60.0}}"
```

**Close**:

```bash
ros2 action send_goal /robotiq_gripper/robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.63, max_effort: 60.0}}"
```

### 1.7 Gripper: attach and detach the cube

In Gazebo, the gripper fingers alone cannot hold the cube reliably. To carry it, close the gripper
around the cube and then attach the cube to the gripper. To put it down, detach it and then open the
gripper. This works in `neo_workshop` and `neo_table`.

Close the gripper around the 80 mm cube with `position: 0.265`: the fingers then end at the cube's
faces.

**Close the gripper around the cube** (in RViz: gripper **Goal State** `grasp_cube`):

```bash
ros2 action send_goal /robotiq_gripper/robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.265, max_effort: 60.0}}"
```

**Attach the cube to the gripper**:

```bash
ros2 service call /link_attacher/attach neo_link_attacher/srv/Attach \
  "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
```

**Detach the cube**:

```bash
ros2 service call /link_attacher/detach neo_link_attacher/srv/Attach \
  "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
```

- Both commands answer `ok=True` when they have worked.
- `attach` fixes the cube at its current position relative to the gripper, even when the gripper is
  far away from it. Close the gripper around the cube first.
- More details: [neo_link_attacher/README.md](neo_link_attacher/README.md).

### 1.8 Stop the simulation

In any terminal, run:

```bash
ros2 run neo_simulation2 stop_sim.sh
```

The command stops the simulation with all of its programs (nodes), including programs left over from
an earlier start that was not stopped properly. It first stops the simulation the same way as Ctrl-C.
Programs that are still running after 25 s are stopped by force (signals SIGINT, SIGTERM and finally
SIGKILL), and each of them is listed with the signal that stopped it.

> **Note:** Do not stop the simulation with Ctrl-C alone. Ctrl-C can leave the Gazebo server or Nav2
> programs running in the background. The next start then fails, or runs every Nav2 program twice.

The last line of the output tells you whether you can start again:

| Last line | Meaning |
| --- | --- |
| `port 11345 free - safe to relaunch` | Everything is stopped. You can start again. |
| `port 11345 still held (TIME_WAIT)`, `Process exited with failure 1` | Everything is stopped. Wait about 30 s before the next start. |
| `STILL RUNNING`, `Process exited with failure 2` | Some programs could not be stopped. Run the command again; if they are still listed, restart the computer. |

For error messages and their solutions, see [Troubleshooting.md](Troubleshooting.md).

---

## 2. Packages

The repository consists of ROS 2 packages, one folder each in `src/`. You do not need to know them to
run the simulation; read a package's `README.md` (function, data flow, files, usage) when you want to
understand or change it.

| Package | Function | Origin |
| --- | --- | --- |
| **Simulation** | | |
| [neo_simulation2](neo_simulation2/README.md) | Gazebo worlds, robot description, `bringup.launch.py` | Neobotix, extended |
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
| `mpo_700_workspace/` | Software of the physical robot. **Not part of this repository and not part of the simulation.** If present, it is placed in `src/mpo_700_workspace/` (excluded by `.gitignore`) and serves as the reference for the simulation settings. Do not build it. |

---

## 3. System overview

The diagram shows how the parts work together. Your own program (the application node) sends goals
to Nav2 and MoveIt, which then command the robot in Gazebo. Arrows show the direction of the messages;
names starting with `/` are the ROS 2 topics, actions and services used.

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
│ world plugins (neo_workshop, neo_table): neo_link_attacher, gazebo_ros_state │
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

The ROS 2 terms used here (topic, action, service, TF, ...) are explained in
[Terminology.md](Terminology.md).
