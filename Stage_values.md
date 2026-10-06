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

The mission is divided into stages, numbered S0 to S21b. The table lists the stages for which values
were recorded, in mission order. The robot drives at the stages marked "Robot position"; the arm moves
at the stages marked "Arm pose".

| Stage | What happens | Value |
| --- | --- | --- |
| S0 | The robot stands at the start position | Robot position Start |
| S1 | The arm moves into the travel pose | Arm pose Home |
| S3b | The robot drives to the pick table | Robot position Pick |
| S5 | The open gripper moves above the cube | Arm pose Pre-grasp |
| S8 | The gripper moves down to the cube and closes | Arm pose Grasp |
| S10 | The arm lifts the cube | Arm pose Lift |
| S13b | The robot drives to the place table | Robot position Place |
| S15 | The arm holds the cube above the place point | Arm pose Pre-place |
| S16 | The arm puts the cube down on the table | Arm pose Place |
| S18 | The gripper is open and moves up, away from the cube | Arm pose Retreat |
| S21b | The robot drives back home | Robot position Home |

## 2. Robot positions

Position of the robot on the map, measured at `base_link`, the centre of the mobile platform. Yaw is
the heading: 0° faces along the x axis of the map, −90° along the negative y axis.

| Position | Stage | x (m) | y (m) | Yaw (°) |
| --- | --- | --- | --- | --- |
| Start | S0 | 0.00 | 0.00 | 0 |
| Pick position | S3b | −1.51 | −3.58 | −90 |
| Place position | S13b | −4.65 | −3.56 | −90 |
| Home | S21b | −0.02 | 0.00 | 0 |

To send the robot to these positions from a terminal, see
[README, section 1.4](README.md#14-drive-to-the-pick-up-drop-and-home-positions).

## 3. Arm poses

Each arm pose is given in two forms: as the six joint angles of the arm, and as the position of the
gripper. Either form can be used as a goal for MoveIt.

| Column | Meaning |
| --- | --- |
| Arm joints | Angles of `shoulder_pan`, `shoulder_lift`, `elbow`, `wrist_1`, `wrist_2`, `wrist_3`, in this order (the joint names start with `ur10`, for example `ur10elbow_joint`) |
| Gripper | Position of the grasp point `grasp_tcp`, between the gripper fingers, relative to `base_link`: the centre of the mobile platform at floor level; x forward, y left, z up. This is not the base of the UR10 arm (`ur10base_link`), which is mounted at x = 0.158 m, y = 0 m, z = 0.766 m in `base_link`, turned by −90° about z. |
| Finger | Gripper opening (`finger_joint`): `0` = open, `0.265` = closed on the 80 mm cube |

| Pose | Stage | Arm joints (rad) | Gripper x, y, z (m) | Finger (rad) |
| --- | --- | --- | --- | --- |
| Home (travel pose) | S1 | 1.49, −2.50, 2.00, 0.00, −1.49, 0.01 | −0.01, 0.20, 1.30 | −0.01 |
| Pre-grasp | S5 | 1.23, −1.97, 2.27, −1.89, −1.57, −0.33 | 0.62, 0.01, 1.01 | 0.00 |
| Grasp | S8 | 1.23, −1.79, 2.48, −2.25, −1.57, −0.34 | 0.61, 0.01, 0.85 | 0.265 |
| Lift | S10 | 1.23, −1.92, 2.35, −2.00, −1.57, −0.34 | 0.61, 0.01, 0.95 | 0.265 |
| Pre-place | S15 | 1.17, −1.96, 2.27, −1.88, −1.56, −0.39 | 0.62, −0.02, 1.00 | 0.265 |
| Place | S16 | 1.18, −1.80, 2.47, −2.24, −1.57, −0.40 | 0.61, −0.01, 0.85 | 0.265 |
| Retreat | S18 | 1.18, −1.97, 2.28, −1.88, −1.57, −0.40 | 0.61, −0.01, 1.00 | 0.00 |

## 4. Using the values in a MoveIt client

The client needs MoveIt, which starts only with `moveit:=True` or `moveit_rviz:=True` (start options
3 and 4 in the [README](README.md#12-start-the-simulation)).

| Item | Value |
| --- | --- |
| Planning group | `ur_manipulator` |
| Planning frame | `base_link` (MPO-700) |
| Joint names, in table order | `ur10shoulder_pan_joint`, `ur10shoulder_lift_joint`, `ur10elbow_joint`, `ur10wrist_1_joint`, `ur10wrist_2_joint`, `ur10wrist_3_joint` |
| Gripper action | `/robotiq_gripper/robotiq_gripper_controller/gripper_cmd` |
| Named states (the arm joint values of the table) | `home`, `pre_grasp`, `grasp`, `lift`, `pre_place`, `place`, `retreat` in group `ur_manipulator`. In RViz: MotionPlanning panel, planning group `ur_manipulator`, **Goal State**. In a client: named target. |

How to use the values:

- **Home:** use the joint values as a joint goal.
- **Other poses:** use pose goals for `grasp_tcp` at the gripper position from the table, with the
  orientation (x, y, z, w) = (0, 1, 0, 0) (gripper pointing down, fingers closing sideways). If you
  use `ur10tool0` as end-effector link instead: 0.188 m higher, orientation (0.707, −0.707, 0, 0).
- **Straight lines:** plan pre-grasp → grasp → lift and pre-place → place → retreat with the Pilz `LIN`
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
