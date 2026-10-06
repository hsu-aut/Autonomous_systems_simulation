# Launch arguments

The simulation is started with one launch file, `bringup.launch.py`. Launch arguments switch its
parts on or off and change settings, for example which world is loaded or which windows open. This
document explains how to pass arguments, how to use the four start options, and lists all arguments.

The other launch files of the simulation are described in
[neo_simulation2/README.md](neo_simulation2/README.md#launch-files).

## Contents

1. [Passing arguments](#1-passing-arguments)
2. [Start options](#2-start-options)
3. [Common combinations](#3-common-combinations)
4. [All arguments](#4-all-arguments)

---

## 1. Passing arguments

Write arguments as `<name>:=<value>` after the file name, separated by spaces:

```bash
ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True moveit_rviz:=True
```

- Switches take the values `True` and `False`.
- An argument that starts a part is named after it: `navigation`, `moveit`, `monitor`, ... Its start
  delay has the same name with `_delay`, for example `moveit_delay`.
- Arguments you do not give keep their default value (see [All arguments](#4-all-arguments)).
- Everything except Gazebo is off by default. An RViz switch also starts its part:
  `navigation_rviz:=True` starts navigation, `moveit_rviz:=True` starts MoveIt. `navigation:=True` and
  `moveit:=True` start them without a window.
- To list all arguments in the terminal, add `--show-args`:

  ```bash
  ros2 launch neo_simulation2 bringup.launch.py --show-args
  ```

## 2. Start options

The four start options of the [README](README.md#12-start-the-simulation):

| Option | Arguments | Starts |
| --- | --- | --- |
| 1. Gazebo only | `teleop:=True` | Gazebo, keyboard driving |
| 2. Gazebo + Navigation | `navigation_rviz:=True` | Gazebo, navigation, navigation RViz |
| 3. Gazebo + MoveIt | `moveit_rviz:=True` | Gazebo, MoveIt, MoveIt RViz |
| 4. Gazebo + Navigation + MoveIt | `navigation_rviz:=True moveit_rviz:=True` | Gazebo, navigation, navigation RViz, MoveIt, MoveIt RViz |

Without any arguments, `bringup.launch.py` starts only Gazebo.

### 2.1 Option 1: driving with the keyboard

`teleop:=True` opens the program `teleop_twist_keyboard` in a separate terminal window. To drive:

1. Click into the `teleop_twist_keyboard` window. It receives your key presses only while it is the
   active window.
2. Hold the key down. The robot stops 0.2 s after the last key press.

| Key | Motion |
| --- | --- |
| `i` / `,` | Forward / backward |
| `j` / `l` | Turn left / right |
| `J` / `L` (with Shift) | Move sideways to the left / right |
| `k` | Stop |
| `q` / `z` | Increase / decrease the speed by 10 % |

You can also run `teleop_twist_keyboard` in a second terminal of your own instead: leave out
`teleop:=True` and run

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> **Note:** Drive with the keyboard only when navigation is not running. With navigation (options 2
> and 4), Nav2 sends the drive commands, and commands from the keyboard would conflict with them.

### 2.2 Option 2: navigation goals

Navigation starts after 20 s, the navigation RViz window after 32 s. To send the robot to a position:

1. Click **Nav2 Goal** in the RViz toolbar.
2. Click on the target position in the map, hold the mouse button, and drag in the direction the robot
   is to face. Release the button.

The robot plans a path and drives to the goal. To send goals from a terminal instead, see
[README, section 1.4](README.md#14-drive-to-the-pick-up-drop-and-home-positions).

### 2.3 Option 3: arm and gripper motions

MoveIt and its RViz window start after 26 s. To move the arm or the gripper, use the
**MotionPlanning** panel in RViz:

1. Select the planning group: `ur_manipulator` (the arm) or `gripper`.
2. Set the goal: drag the marker at the tool of the arm, or select a stored pose under **Goal State**
   (for example `up` for the arm, `open` or `close` for the gripper). To grip the cube, use
   `grasp_cube` instead of `close`: it stops the fingers at the cube's faces.
3. Click **Plan & Execute**.

### 2.4 Option 4: navigation and MoveIt

Navigation starts after 20 s, MoveIt with its RViz window after 26 s, the navigation RViz after 32 s;
the start takes about 40 s. Navigation goals work as in [option 2](#22-option-2-navigation-goals), arm
motions as in [option 3](#23-option-3-arm-and-gripper-motions).

### 2.5 Navigation, MoveIt and their RViz windows

Navigation and MoveIt each have two switches, and all four are `False` by default:

- `navigation` and `moveit` start the component **without** its RViz window.
- `navigation_rviz` and `moveit_rviz` start the component **and** its RViz window.

A component starts when at least one of its two switches is `True`. It is always started only once,
also when both switches are `True`. The RViz window opens only with the RViz switch.

| You pass | MoveIt | MoveIt RViz |
| --- | :---: | :---: |
| nothing | – | – |
| `moveit:=True` | ✓ | – |
| `moveit_rviz:=True` | ✓ | ✓ |
| `moveit:=True moveit_rviz:=True` | ✓ | ✓ (the same as `moveit_rviz:=True` alone) |
| `moveit:=False moveit_rviz:=True` | ✓ | ✓ (the RViz switch starts MoveIt anyway) |

Navigation works the same way with `navigation` and `navigation_rviz`.

Use the switches without RViz when your own program sends the goals, or to reduce the computer load:
RViz is the heaviest window. For example, MoveIt without its window and navigation with its window:

```bash
ros2 launch neo_simulation2 bringup.launch.py moveit:=True navigation_rviz:=True
```

## 3. Common combinations

| You want to ... | Add |
| --- | --- |
| plan arm and gripper motions in RViz | `moveit_rviz:=True` |
| let the robot navigate, with the map in RViz | `navigation_rviz:=True` |
| start MoveIt without its window, for your own program (reduces the computer load) | `moveit:=True` |
| start navigation without its window, for your own program | `navigation:=True` |
| run without any window | `gazebo_gui:=False` (for navigation or MoveIt, add `navigation:=True` or `moveit:=True`) |
| see the robot state window (joints, base pose, gripper pose) | `monitor:=True` |
| test grasping at a single table, without navigation | `world:=neo_table moveit_rviz:=True` |
| use navigation only, without the arm | `arm_type:=none navigation_rviz:=True` |
| give a slow computer more time: start navigation and MoveIt later | `navigation_delay:=30 moveit_delay:=40` |
| start without the cube on the table | `spawn_cube:=False` |
| place your own objects (in any world) | `objects:=<file>`, in the format of `neo_sim_objects/config/objects.yaml` |

The cube: by default (`spawn_cube:=True`) it is placed on the first cafe table of `neo_workshop`,
10 s after the start. In other worlds, nothing is placed unless you give `objects:=<file>`;
`neo_table` already contains its own cube.

Complete commands for some of these combinations:

```bash
# Navigation and MoveIt; show the navigation map, MoveIt without its window
ros2 launch neo_simulation2 bringup.launch.py navigation_rviz:=True moveit:=True

# Run without any window
ros2 launch neo_simulation2 bringup.launch.py gazebo_gui:=False

# Test grasping at a single table, without navigation
ros2 launch neo_simulation2 bringup.launch.py world:=neo_table moveit_rviz:=True

# Navigation only, on a driving track, without the arm
ros2 launch neo_simulation2 bringup.launch.py world:=neo_track1 map:=neo_track1 arm_type:=none navigation_rviz:=True
```

## 4. All arguments

| Argument | Default | Description |
| --- | --- | --- |
| **Simulation** | | |
| `world` | `neo_workshop` | World: `neo_workshop`, `neo_table` (one table with a cube), `neo_track1`, `neo_track2`, or the full path of a `.world` file |
| `arm_type` | `ur10` | Arm type. `none` removes the arm; then do not start MoveIt. |
| `gazebo_gui` | `True` | Open the Gazebo window. `False` runs the simulation without the window. |
| **Objects** | | |
| `spawn_cube` | `True` | Place objects: in `neo_workshop` the cube on the first cafe table (`neo_sim_objects/config/objects.yaml`); in other worlds only the objects of `objects`. `neo_table` has its own cube. |
| `objects` | empty | Object file for `spawn_cube`, in the format of `neo_sim_objects/config/objects.yaml`. Empty: the default cube, in `neo_workshop` only. |
| **Navigation** | | |
| `navigation` | `False` | Start navigation, without its RViz window |
| `map` | `neo_workshop` | Navigation map: `neo_workshop`, `neo_track1`, `neo_track2`, or the full path of a `.yaml` file. Set it together with `world`. |
| `navigation_rviz` | `False` | Start navigation together with its RViz window |
| `use_amcl` | `False` | Use Nav2 AMCL instead of `neo_localization2` to localise the robot. An argument of `navigation.launch.py`, passed through. |
| **Arm** | | |
| `moveit` | `False` | Start MoveIt, without its RViz window |
| `moveit_rviz` | `False` | Start MoveIt together with its RViz window |
| **Tools** | | |
| `monitor` | `False` | Open the monitor window (joint states, base pose, gripper pose) |
| `tcp_frame` | `ur10tool0` | Gripper frame shown in the monitor; `grasp_tcp` is the point between the fingers |
| `teleop` | `False` | Open the keyboard driving window |
| **Start delays** (seconds; increase them on a slow computer) | | |
| `gazebo_gui_delay`, `cube_delay`, `navigation_delay`, `moveit_delay`, `navigation_rviz_delay`, `monitor_delay` | `6`, `10`, `20`, `26`, `32`, `36` | Time after the start of the simulation; the order is shown in the [start-up sequence](neo_simulation2/README.md#start-up-sequence) |

> **Note:** `--show-args` lists about 35 arguments. Those not listed above belong to the launch files
> that `bringup.launch.py` includes (for example `use_sim_time`, `use_docking_adapter`); keep their
> default values.
>
> Older versions used other names (`use_navigation`, `use_moveit`, `gui`, `nav_delay`, ...). These have
> no effect any more; `bringup.launch.py` prints a warning with the new name when one is passed.

> **Note:** The project is configured and tested for `my_robot:=mpo_700` with `arm_type:=ur10` (the
> defaults). With `arm_type:=ur5`, `ur5e` or `ur10e`, the arm and gripper controllers start; MoveIt and
> navigation are tested with `ur10` only. The other robot types originate from Neobotix and are not
> configured for this project.
