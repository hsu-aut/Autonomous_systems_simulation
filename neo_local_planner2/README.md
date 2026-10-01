# neo_local_planner2

This package provides the Nav2 controller plugin that converts the planned path into velocity commands:
forward, lateral and rotational velocity.

| Property | Value |
| --- | --- |
| Origin | Neobotix |
| Type | Nav2 controller plugin (C++) |
| Started by | Nav2 `controller_server`, which loads the plugin as `FollowPath` and calls it at 50 Hz. No launch command is required. |
| Configuration | `controller_server` section of `neo_simulation2/configs/mpo_700/navigation.yaml` |

## Data flow

```text
                                ┌───────────────────────────────┐
global path (planner_server) ──▶│ neo_local_planner2            │
        robot pose and speed ──▶│ (plugin in controller_server) │──▶ /cmd_vel
   local costmap (obstacles) ──▶│                               │
                                └───────────────────────────────┘
```

## Operation

- The plugin follows the path by steering towards a look-ahead point.
- It reduces the speed near obstacles (high cost in the local costmap).
- It drives laterally, as the MPO-700 can (`differential_drive: false`).
- Near the goal, it corrects position and heading.

Main parameters: velocity limits (`max_vel_x`, `max_rot_vel`) and acceleration limits (`acc_lim_x`). The
values are those of the physical robot.

## Files

```text
neo_local_planner2/
├── src/NeoLocalPlanner.cpp          plugin source
├── include/NeoLocalPlanner.hpp      plugin header
└── neo_local_planner2_plugin.xml    plugin registration for Nav2
```

Neobotix documentation: <https://neobotix-docs.de/ros/packages/neo_local_planner.html>
