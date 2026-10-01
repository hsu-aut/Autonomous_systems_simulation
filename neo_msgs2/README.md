# neo_msgs2

This package defines message types for Neobotix robot hardware: relay board, IO board, ultrasonic
sensors, emergency stop and safety scanners.

| Property | Value |
| --- | --- |
| Origin | Neobotix |
| Type | Message definitions |
| Used by the simulation | No. The package is built because `neo_srvs2` depends on it. |

## Files

```text
neo_msgs2/
└── msg/    message definitions, one .msg file per type
```

To display a message definition, run:

```bash
ros2 interface show neo_msgs2/msg/EmergencyStopState
```
