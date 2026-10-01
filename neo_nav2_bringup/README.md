# neo_nav2_bringup

This package contains the launch files that start Nav2, the ROS 2 navigation stack, for Neobotix robots.
It contains no source code.

| Property | Value |
| --- | --- |
| Origin | Neobotix |
| Type | Launch files, default parameters, RViz configurations |
| Started by | `neo_simulation2/launch/navigation.launch.py`, which `bringup.launch.py` starts. No separate launch command is required. |
| Configuration | `neo_simulation2/configs/mpo_700/navigation.yaml` |

## Launch files

| Launch file | Nodes | Function |
| --- | --- | --- |
| `localization_neo.launch.py` | `map_server`, `neo_localization2_node` | Load the map; localise the robot (default) |
| `localization_amcl.launch.py` | `map_server`, `amcl` | Same function with AMCL (`use_amcl:=True`) |
| `navigation_neo.launch.py` | `planner_server`, `controller_server`, `behavior_server`, `bt_navigator`, `waypoint_follower` | Plan paths and drive |
| `mapping.launch.py` | `slam_toolbox` | Build a new map |

Each launch file also starts a lifecycle manager, which configures and activates its nodes in order.

## Data flow

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

- `bt_navigator` executes a behavior tree: compute a path, follow it, and recompute it once per second.
- When the robot cannot progress, the behavior tree runs recovery actions: clear the costmaps, rotate,
  wait, reverse.
- The behavior trees used by the simulation are in `neo_simulation2/configs/mpo_700/behavior_trees/`.

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
