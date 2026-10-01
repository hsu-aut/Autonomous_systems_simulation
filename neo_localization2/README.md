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

Neobotix documentation: <https://neobotix-docs.de/ros/packages/neo_localization.html>
