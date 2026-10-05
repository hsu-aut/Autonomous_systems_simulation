# neo_nav2_bringup

Nav2 is the navigation software of ROS 2: it finds out where the robot is on the map, plans a path to a
goal and drives the robot along it. This package contains the launch files that start Nav2 for
Neobotix robots; it contains no source code.

You do not start this package yourself: `bringup.launch.py` starts it in start options 2 and 4 (see the
[README](../README.md#12-start-the-simulation)).

| Property | Value |
| --- | --- |
| Origin | Neobotix |
| Type | Launch files, default parameters, RViz configurations |
| Started by | `neo_simulation2/launch/navigation.launch.py`, which `bringup.launch.py` starts. No separate launch command is required. |
| Configuration | `neo_simulation2/configs/mpo_700/navigation.yaml` |

## How navigation works

Navigation runs in three parts:

1. **Localisation:** `neo_localization2` compares the lidar scans with the map and so determines where
   the robot is on the map.
2. **Path planning:** when a goal arrives, `planner_server` computes a path on the map from the robot
   to the goal, around the obstacles in the map and those the lidars currently see.
3. **Driving:** `controller_server` follows the path, avoids obstacles close to the robot, and sends
   velocity commands to the robot on `/cmd_vel`.

`bt_navigator` coordinates these parts with a behavior tree: compute a path, follow it, and recompute
it once per second. When the robot cannot make progress, the behavior tree runs recovery actions:
clear the obstacle maps (costmaps), rotate, wait, reverse. The behavior trees used by the simulation
are in `neo_simulation2/configs/mpo_700/behavior_trees/`.

```text
              goal: /navigate_to_pose  (action, from an application or RViz)
                                              │
                          ┌───────────────────▼──────────────────┐
                          │ bt_navigator   (behavior tree)       │
                          └───────┬─────────────────────┬────────┘
                     compute path │                     │ follow path
                                  │                     │
                ┌─────────────────▼────────┐    ┌───────▼──────────────────────┐
/map ──────────▶│ planner_server           │    │ controller_server            │
                │ global path on the map   │    │ neo_local_planner2 (plugin)  │────▶ /cmd_vel
                │ global costmap           │    │ local costmap                │
                └─────────────▲────────────┘    └─────────────▲────────────────┘
                              │                               │
                              │ lidar_N/scan_filtered         │ lidar_N/scan_filtered

                       ┌───────────────────┐
              /scan ──▶│ neo_localization2 │
               /map ──▶│ (or amcl)         │──▶ TF map → odom   (robot position on the map)
TF odom → base_link ──▶│                   │
                       └───────────────────┘
```

## Sending a goal

A goal is a position on the map and the direction the robot is to face there. You can send it in RViz
or from a terminal.

### In RViz

Start the simulation with the navigation RViz window (`navigation_rviz:=True`, start option 2). Click
**Nav2 Goal** in the RViz toolbar, click on the target position in the map, and drag in the direction
the robot is to face.

### From a terminal

The simulation must be running with navigation in `neo_workshop` (start option 2 or 4). These
commands send the robot to the pick-up, drop and home positions of the pick-and-place mission
([Stage_values.md](../Stage_values.md#2-robot-positions)):

```bash
# Pick-up position, in front of the pick table (x -1.51 m, y -3.58 m, yaw -90°)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -1.51, y: -3.58}, orientation: {z: -0.7071, w: 0.7071}}}}"

# Drop position, in front of the place table (x -4.65 m, y -3.56 m, yaw -90°)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -4.65, y: -3.56}, orientation: {z: -0.7071, w: 0.7071}}}}"

# Home, the start position (x -0.02 m, y 0.00 m, yaw 0°)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -0.02, y: 0.0}, orientation: {z: 0.0, w: 1.0}}}}"
```

- The command ends when the robot has reached the goal (`SUCCEEDED`) or navigation has given up
  (`ABORTED`). Ctrl-C cancels the goal, and the robot stops.
- With `--feedback` after `send_goal`, the command prints the remaining distance
  (`distance_remaining`) while the robot drives.

**Other positions.** Replace `x`, `y` and the orientation. ROS 2 writes the direction (yaw angle) as a
quaternion: `z` = sin(yaw / 2), `w` = cos(yaw / 2). Values for the main directions:

| Yaw | `z` | `w` |
| --- | --- | --- |
| 0° | `0.0` | `1.0` |
| 90° | `0.7071` | `0.7071` |
| −90° | `-0.7071` | `0.7071` |
| 180° | `1.0` | `0.0` |

## Launch files

| Launch file | Nodes | Function |
| --- | --- | --- |
| `localization_neo.launch.py` | `map_server`, `neo_localization2_node` | Load the map; localise the robot (default) |
| `localization_amcl.launch.py` | `map_server`, `amcl` | Same function with AMCL (`use_amcl:=True`) |
| `navigation_neo.launch.py` | `planner_server`, `controller_server`, `behavior_server`, `bt_navigator`, `waypoint_follower` | Plan paths and drive |
| `mapping.launch.py` | `slam_toolbox` | Build a new map |

Each launch file also starts a lifecycle manager, which configures and activates its nodes in the
right order.

## Files

```text
neo_nav2_bringup/
├── launch/    launch files listed above, and rviz_launch.py
├── config/    default parameters for a generic robot (not used by the simulation)
└── rviz/      RViz configurations
```

At start-up, the launch files rewrite the parameter file (`RewrittenYaml`): they set the map file,
`use_sim_time` and the namespace wherever these keys exist in the file.

Neobotix documentation: <https://neobotix-docs.de/ros/packages/neo_nav2_bringup.html>
