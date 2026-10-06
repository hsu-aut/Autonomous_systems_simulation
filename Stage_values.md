# Pick-and-Place Mission: Stage Values

This document contains the recorded values of a complete pick-and-place mission in the world
`neo_workshop`: the robot drives to the pick table, picks up the cube, drives to the place table, puts
the cube down and returns home. Use these values when you write your own program for the mission (a
MoveIt client).

## Contents

1. [Mission overview](#1-mission-overview)
2. [Robot positions](#2-robot-positions)
3. [Arm poses](#3-arm-poses)
4. [Using the values in a MoveIt client](#4-using-the-values-in-a-moveit-client)

---

## 1. Mission overview

The mission is divided into stages S0 to S10, in mission order. S0 is the starting state; in each
further stage, either the mobile platform drives (stages marked "Robot position") or the arm moves
(stages marked "Arm pose"). The arm uses only three poses: `home`, `pregrasp` and `grasp`
([section 3](#3-arm-poses)).

| Stage | What happens | Value |
| --- | --- | --- |
| S0 | The robot stands at the start position | Robot position Start |
| S1 | The arm moves into the travel pose | Arm pose `home` |
| S2 | The robot drives to the pick table | Robot position Pick |
| S3 | The open gripper moves above the cube | Arm pose `pregrasp` |
| S4 | The gripper moves down to the cube and closes | Arm pose `grasp` |
| S5 | The arm lifts the cube | Arm pose `pregrasp` |
| S6 | The robot drives to the place table | Robot position Place |
| S7 | The arm holds the cube above the place point | Arm pose `pregrasp` |
| S8 | The arm puts the cube down on the table | Arm pose `grasp` |
| S9 | The gripper is open and moves up, away from the cube | Arm pose `pregrasp` |
| S10 | The robot drives back home | Robot position Home |

## 2. Robot positions

Position of the mobile platform on the map, measured at `base_link`, the centre of the platform. Yaw is
the heading: 0° faces along the x axis of the map, −90° along the negative y axis.

| Position | Stage | x (m) | y (m) | Yaw (°) |
| --- | --- | --- | --- | --- |
| Start | S0 | 0.00 | 0.00 | 0 |
| Pick position | S2 | −1.51 | −3.58 | −90 |
| Place position | S6 | −4.65 | −3.56 | −90 |
| Home | S10 | −0.02 | 0.00 | 0 |

To drive the mobile platform to these positions from a terminal, see
[README, section 1.4](README.md#14-mobile-platform-drive-autonomously-to-the-pick-place-and-home-positions).

## 3. Arm poses

The arm uses three poses, stored in MoveIt as named states. To select them in RViz, see
[README, section 1.5](README.md#15-manipulator-arm-move-to-the-mission-poses).

| Pose | Arm position | Stages | Arm joints (rad) | Gripper x, y, z (m) |
| --- | --- | --- | --- | --- |
| `home` | Folded above the platform (travel pose) | S1 | 1.49, −2.50, 2.00, 0.00, −1.49, 0.01 | −0.01, 0.20, 1.30 |
| `pregrasp` | Gripper 16 cm above `grasp` | S3, S5, S7, S9 | 1.23, −1.97, 2.27, −1.89, −1.57, −0.33 | 0.62, 0.01, 1.01 |
| `grasp` | Gripper around the cube on the table | S4, S8 | 1.23, −1.79, 2.48, −2.25, −1.57, −0.34 | 0.61, 0.01, 0.85 |

- **Arm joints:** `shoulder_pan`, `shoulder_lift`, `elbow`, `wrist_1`, `wrist_2`, `wrist_3`, in this
  order.
- **Gripper:** position of `grasp_tcp`, the point between the fingers, in `base_link`: the centre of
  the platform at floor level; x forward, y left, z up.
- `pregrasp` and `grasp` are used at both tables, for picking and for placing. They fit only when the
  platform is at the pick or place position.

## 4. Using the values in a MoveIt client

The client needs MoveIt, which starts only with `moveit:=True` or `moveit_rviz:=True` (start options
3 and 4 in the [README](README.md#12-start-the-simulation)).

| Item | Value |
| --- | --- |
| Planning group | `ur_manipulator` |
| Planning frame | `base_link`: the centre of the MPO-700 platform at floor level. The arm base `ur10base_link` is at x = 0.158 m, y = 0 m, z = 0.766 m in it, turned by −90° about z. |
| Joint names, in table order | `ur10shoulder_pan_joint`, `ur10shoulder_lift_joint`, `ur10elbow_joint`, `ur10wrist_1_joint`, `ur10wrist_2_joint`, `ur10wrist_3_joint` |
| Gripper action | `/robotiq_gripper/robotiq_gripper_controller/gripper_cmd` |
| Named states (the arm joint values of the table) | `home`, `pregrasp`, `grasp` in group `ur_manipulator`. In RViz: MotionPlanning panel, planning group `ur_manipulator`, **Goal State**. In a client: named target. |

How to use the values:

- **`home`:** use the joint values as a joint goal.
- **`pregrasp`, `grasp`:** use pose goals for `grasp_tcp` at the gripper position from the table,
  with the orientation (x, y, z, w) = (0, 1, 0, 0) (gripper pointing down, fingers closing sideways).
  If you use `ur10tool0` as end-effector link instead: 0.188 m higher, orientation
  (0.707, −0.707, 0, 0).
- **Straight lines:** plan `pregrasp` → `grasp` and `grasp` → `pregrasp` with the Pilz `LIN`
  planner, so that the gripper moves in a straight line; plan all other motions with OMPL.
- **Gripper:** open with position `0.0`; close on the cube with position `0.265` and max effort `60` (MoveIt gripper pose `grasp_cube`).
  The fingers end at the cube's faces. Fingers and cube do not collide (set by `spawn_objects`), so an
  off-centre cube is not pushed away; the cube is held by attaching it (below).
- **Tables:** add both tables to the planning scene, so that MoveIt plans around them. Each table
  consists of three boxes around the table centre (pick table −1.492, −4.548; place table −4.668,
  −4.529 on the map):

  | Box | Size (m) | Centre height z (m) |
  | --- | --- | --- |
  | Top | 0.913 × 0.913 × 0.04 | 0.750 |
  | Column | 0.042 × 0.042 × 0.74 | 0.365 |
  | Foot | 0.56 × 0.56 × 0.04 | 0.015 |

  Convert the positions to `base_link` with the robot position.
- **Holding the cube:** attach the cube (an 80 mm box) to `grasp_tcp` in the planning scene, so that MoveIt treats it
  as part of the gripper. In Gazebo, also call `/link_attacher/attach`, so that the cube moves with
  the gripper (see [neo_link_attacher](neo_link_attacher/README.md)).
