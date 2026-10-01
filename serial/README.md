# serial

This package is a C++ library for communication over a serial port (USB-serial cable).

| Property | Value |
| --- | --- |
| Origin | Third-party: William Woodall, ROS 2 version |
| Type | C++ library |
| Used by the simulation | No. Only `robotiq_driver` (the hardware driver of the gripper, also not used) depends on it. |

## Files

```text
serial/
├── include/serial/serial.h    interface: class Serial
├── src/                       implementation for Linux, macOS and Windows
└── README.upstream.md         original README with license and authors
```

Original README, including the MIT license and the authors: [README.upstream.md](README.upstream.md).
