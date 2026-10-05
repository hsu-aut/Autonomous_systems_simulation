# neo_localization2

This package determines the position of the robot on the map by matching the lidar scans against the
map.

| Property | Value |
| --- | --- |
| Origin | Neobotix (alternative to Nav2 AMCL); one local change |
| Type | ROS 2 node (C++) |
| Started by | Navigation, which `bringup.launch.py` starts. No separate launch command is required. |
| Configuration | `neo_localization2_node` section of `neo_simulation2/configs/mpo_700/navigation.yaml` |

## Data flow

```text
                       ┌────────────────────────┐
              /scan ──▶│ neo_localization2_node │──▶ TF map → odom
               /map ──▶│                        │──▶ /amcl_pose, /map_pose
TF odom → base_link ──▶│                        │──▶ /particlecloud
       /initialpose ──▶│                        │──▶ /map_tile
                       └────────────────────────┘
```

## Operation

- Odometry (`odom → base_link`) drifts over time. The node corrects the drift by publishing
  `map → odom`.
- Every 100 ms, the node fits the latest lidar scans to the map and publishes the best pose.
- Every 2 s, a background thread prepares a new section of the map around the robot.
- To set the robot pose manually, use **2D Pose Estimate** in RViz. RViz publishes the pose on
  `/initialpose`.

## Files

```text
neo_localization2/
├── src/neo_localization_node.cpp    node source
└── include/neo_localization/        scan-to-map solver and map functions
```

## Local changes

- On shutdown, the node stops its background thread before it exits. Previously it aborted with exit
  code −6.
- The `map → odom` transform is stamped 1 s after the odometry it is based on, so that it stays valid
  until the next update (as in Nav2 AMCL). The 1 s was added directly to the nanoseconds field, which
  produced invalid time stamps (nanoseconds ≥ 10⁹) and also moved the stamp of `/amcl_pose` 1 s into
  the future. Both are corrected: the transform uses valid time arithmetic, `/amcl_pose` carries the
  time of the odometry.
- In the simulation the node runs on simulation time (`use_sim_time: True` in
  `neo_simulation2/configs/*/navigation.yaml`).

Neobotix documentation: <https://neobotix-docs.de/ros/packages/neo_localization.html>
