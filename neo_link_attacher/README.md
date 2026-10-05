# neo_link_attacher

This package provides a Gazebo world plugin that attaches an object to the robot and releases it again.
Applications use it to carry objects with the gripper.

| Property | Value |
| --- | --- |
| Origin | This project |
| Type | Gazebo world plugin (C++), service definitions |
| Started by | Gazebo, when it loads `neo_workshop.world` or `neo_table.world`. No launch command is required. |

## Purpose

- The simulated gripper fingers cannot hold an object reliably by friction.
- While an object is carried, the plugin connects the object to the robot wrist with a temporary
  fixed joint. The joint is removed when the object is released.

## Data flow

```text
                                      ┌───────────────────────┐
             /link_attacher/attach ──▶│ neo_link_attacher     │──▶ joins object and robot link
             /link_attacher/detach ──▶│ (Gazebo world plugin) │──▶ separates them
/link_attacher/set_collide_bitmask ──▶│                       │──▶ changes which parts collide
                                      └───────────────────────┘
```

| Service | Effect |
| --- | --- |
| `/link_attacher/attach` | Attaches an object link to a robot link (for example `ur10wrist_3_link`) at its current position |
| `/link_attacher/detach` | Removes the joint; the object is free |
| `/link_attacher/set_collide_bitmask` | Sets the collision bitmask of a link. Typical use: gripper fingers and object no longer collide with each other, while both still collide with the table. |

> **Note:** Gazebo merges links that are connected by fixed joints. In Gazebo, the gripper is therefore
> part of `ur10wrist_3_link`.

## Files

```text
neo_link_attacher/
├── src/link_attacher.cpp        plugin source
├── srv/Attach.srv               request: model1, link1, model2, link2; response: ok, message
└── srv/SetCollideBitmask.srv    request: model, link, bitmask; response: ok, message
```

## Manual use

Prerequisite: the simulation is running (`bringup.launch.py`), and the cube is in the world.

1. Attach the cube to the robot wrist:

   ```bash
   ros2 service call /link_attacher/attach neo_link_attacher/srv/Attach \
     "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
   ```

   Expected response: `ok=True, message='attached mpo_700/ur10wrist_3_link<->cube/link'`. The cube now
   moves with the arm.

2. Release the cube:

   ```bash
   ros2 service call /link_attacher/detach neo_link_attacher/srv/Attach \
     "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
   ```

   Expected response: `ok=True`. Gravity and contacts act on the cube again.

| Request field | Value | Meaning |
| --- | --- | --- |
| `model1` | `mpo_700` | Gazebo model name of the robot |
| `link1` | `ur10wrist_3_link` | Robot link that holds the object (the gripper is part of this link in Gazebo) |
| `model2` | `cube` | Gazebo model name of the object |
| `link2` | `link` | Link of the object |

> **Note:**
>
> - `attach` fixes the object at its current position relative to the wrist, also when the gripper is
>   far away. Close the gripper around the object first.
> - `detach` removes only a joint created by `attach`. Without a previous `attach`, the response is
>   `ok=False, message='not attached: ...'` and nothing changes.
> - Neither service moves the gripper fingers. To open or close the gripper, send a goal to the
>   gripper action `/robotiq_gripper/robotiq_gripper_controller/gripper_cmd`.

After modifying the C++ source, rebuild the workspace and restart the simulation.
