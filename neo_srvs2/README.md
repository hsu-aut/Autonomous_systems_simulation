# neo_srvs2

This package defines service types for Neobotix robot hardware: relays, LEDs, emergency stop, safety
fields, LCD and the wheels of the MPO-700.

| Property | Value |
| --- | --- |
| Origin | Neobotix |
| Type | Service definitions (uses messages from `neo_msgs2`) |
| Used by the simulation | No |

## Files

```text
neo_srvs2/
└── srv/    service definitions, one .srv file per type
```

To display a service definition, run:

```bash
ros2 interface show neo_srvs2/srv/RelayBoardSetEMStop
```
