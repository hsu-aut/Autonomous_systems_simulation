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

To release the cube, run:

```bash
ros2 service call /link_attacher/detach neo_link_attacher/srv/Attach \
  "{model1: mpo_700, link1: ur10wrist_3_link, model2: cube, link2: link}"
```

After modifying the C++ source, rebuild the workspace and restart the simulation.
