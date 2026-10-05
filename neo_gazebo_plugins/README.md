# neo_gazebo_plugins

This package provides `neo_planar_move`, a Gazebo model plugin that moves the simulated robot base
according to velocity commands.

| Property | Value |
| --- | --- |
| Origin | This project |
| Type | Gazebo model plugin (C++) |
| Started by | Gazebo, when the robot model is loaded. No launch command is required. |
| Configuration | `neo_simulation2/components/common_macro/gazebo_object_controller_macro.xacro` |

## Data flow

```text
                             ┌───────────────────────┐
                             │ neo_planar_move       │──▶ /odom
 /cmd_vel  (Nav2, teleop) ──▶│ (Gazebo model plugin) │──▶ TF odom → base_link
                             │                       │──▶ base motion in Gazebo
                             └───────────────────────┘
```

## Behaviour

- The physical MPO-700 steers four wheels. In simulation, the plugin moves the complete base at the
  commanded velocity.
- The plugin applies the latest command at 100 Hz (`update_rate`) and publishes `/odom` and the TF
  `odom → base_link` at 50 Hz (`publish_rate`). Both are set in
  `neo_simulation2/components/common_macro/gazebo_object_controller_macro.xacro`, from the values in
  the robot's `*_gazebo.urdf.xacro`.
- The base stops when no command arrives for 0.2 s (`cmd_timeout`).
- The plugin sets only the forward, lateral and rotational velocity. Gravity keeps the base on its
  wheels.

## Files

```text
neo_gazebo_plugins/
├── src/neo_planar_move.cpp        plugin source
└── include/neo_gazebo_plugins/    plugin header
```

## Maintenance

After modifying the C++ source, rebuild the workspace and restart the simulation.
