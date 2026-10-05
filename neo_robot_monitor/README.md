# neo_robot_monitor

This package provides a window that displays the state of the robot in real time. The monitor reads
data only; it does not command the robot.

| Property | Value |
| --- | --- |
| Origin | This project |
| Type | ROS 2 node with Qt window (Python) |
| Started by | `bringup.launch.py` with `monitor:=True` (default `False`), or standalone (see [Standalone start](#standalone-start)) |

Displayed values:

- robot position (x, y, heading) in the `map` and `odom` frames
- measured and commanded base velocity
- gripper position and opening
- angle and velocity of each arm joint

## Data flow

```text
                         ┌─────────┐
        /joint_states ──▶│ monitor │
/dynamic_joint_states ──▶│ (10 Hz) │
                /odom ──▶│         │──▶ monitor window
             /cmd_vel ──▶│         │
                   TF ──▶│         │
                         └─────────┘
```

The ROS interface runs in a background thread. The window reads the latest values every 100 ms.

## Files

```text
neo_robot_monitor/
├── neo_robot_monitor/monitor.py    node and window (Qt)
└── launch/monitor.launch.py        starts the node
```

## Standalone start

```bash
ros2 launch neo_robot_monitor monitor.launch.py

# Display the grasp point between the fingers instead of the tool flange
ros2 launch neo_robot_monitor monitor.launch.py tcp_frame:=grasp_tcp
```

| Option | Default | Description |
| --- | --- | --- |
| `tcp_frame` | `ur10tool0` | Gripper frame to display; `grasp_tcp` is the point between the fingers |
| `map_frame`, `odom_frame`, `base_frame` | `map`, `odom`, `base_link` | Frame names |
| `use_sim_time` | `True` | Keep `True` in simulation; otherwise positions are shown as unavailable |
