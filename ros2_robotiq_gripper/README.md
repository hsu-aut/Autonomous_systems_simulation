# ros2_robotiq_gripper

This repository provides the 3D model of the Robotiq 2F-140 gripper (`robotiq_description`). The
simulated gripper is built from this model.

| Property | Value |
| --- | --- |
| Origin | PickNik Robotics; local changes listed below |
| Type | Robot description (xacro, meshes); hardware driver and controller (not used) |
| Started by | Not started. The robot description of `neo_simulation2` includes the model. |

| Sub-package | Content | Used by the simulation |
| --- | --- | --- |
| `robotiq_description` | Gripper model (xacro macros, meshes) | Yes |
| `robotiq_driver` | USB driver for the physical gripper, uses `serial` | No |
| `robotiq_controllers` | Activation controller for the physical gripper | No |
| `robotiq_hardware_tests` | Test tool | No (excluded from the build) |

## Data flow

Gripper model:

```text
┌────────────────────────┐      ┌───────────────────┐      ┌────────┐
│ robotiq_description    │ ───▶ │ robot description │ ───▶ │ Gazebo │
│ (xacro macros, meshes) │      │ (neo_simulation2) │      │        │
└────────────────────────┘      └───────────────────┘      └────────┘
```

Gripper command (action `/robotiq_gripper/robotiq_gripper_controller/gripper_cmd`):

```text
┌──────────────────────┐      ┌────────────────────────────┐      ┌──────────────┐
│ gripper_action_relay │ ───▶ │ robotiq_gripper_controller │ ───▶ │ finger_joint │
└──────────────────────┘      └────────────────────────────┘      └──────────────┘
```

- The gripper has one actuated joint, `finger_joint` (0 rad = open, 0.7 rad = closed). The other finger
  joints follow it.
- The gripper controller is configured in `neo_simulation2/configs/ur_config/ur10/ur_controllers.yaml`.

## Files

```text
ros2_robotiq_gripper/
├── robotiq_description/urdf/      robotiq_2f_140_macro.urdf.xacro and parts; UR adapter plate
├── robotiq_description/meshes/    visual and collision meshes
├── robotiq_driver/                hardware driver (C++); not used
├── robotiq_controllers/           hardware controller (C++); not used
├── HUMBLE_PIN.md                  reason for the pinned driver revision
├── GRIPPER_INTEGRATION.md         development report: gripper integration into the simulation
└── README.upstream.md             original README of PickNik Robotics
```

## Local changes

- `robotiq_description`: the lower limit of `finger_joint` is −0.01 rad, because Gazebo settles slightly
  below 0. The meshes are resolvable by Gazebo. The [build command](../Installation.md#5-build-the-workspace)
  therefore contains `--allow-overriding robotiq_description`.
- `robotiq_driver` and `robotiq_controllers` are pinned to an older revision that builds on Humble. See
  [HUMBLE_PIN.md](HUMBLE_PIN.md).

Development report on the integration of the gripper into the simulation (background information):
[GRIPPER_INTEGRATION.md](GRIPPER_INTEGRATION.md).

Original README of PickNik Robotics: [README.upstream.md](README.upstream.md).
