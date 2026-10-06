# neo_mpo_moveit2 (package `neo_ur_moveit_config`)

This package contains the MoveIt 2 configuration for the UR10 arm and the Robotiq gripper of the
MPO-700. MoveIt plans collision-free arm motions and executes them through the arm controller.

| Property | Value |
| --- | --- |
| Origin | Neobotix; extended for this project (Pilz straight-line planner, corrections) |
| Type | MoveIt configuration, launch file |
| Started by | `bringup.launch.py` with `moveit:=True` (without RViz) or `moveit_rviz:=True` (with RViz), 26 s after the simulation. Both default to `False`. |

> **Important:** Do not start MoveIt a second time. Two `move_group` instances answer the same requests,
> and goals fail.

## Data flow

```text
                         ┌────────────┐
         /move_action ──▶│ move_group │
          /compute_ik ──▶│            │──▶ /joint_trajectory_controller/follow_joint_trajectory
/apply_planning_scene ──▶│            │──▶ /robotiq_gripper/robotiq_gripper_controller/gripper_cmd
        /joint_states ──▶│            │
    robot description ──▶│            │
                         └────────────┘
```

- `move_group` maintains a planning scene: the robot and all objects reported to it through
  `/apply_planning_scene`. Every plan avoids these objects.
- With `use_gazebo:=true` (set by `bringup.launch.py`), MoveIt uses the robot description of
  `neo_simulation2` and therefore plans for the simulated robot.

| Planner | Pipeline | Used for |
| --- | --- | --- |
| OMPL (RRTConnect) | `move_group` (default) | Free motions along any collision-free path |
| Pilz `LIN` | `pilz_industrial_motion_planner` | Straight-line motions near tables and objects |

## Files

```text
neo_mpo_moveit2/
└── neo_ur_moveit_config/
    ├── launch/neo_ur_moveit.launch.py    starts move_group and the MoveIt RViz window
    ├── srdf/mpo_700.srdf.xacro           planning groups (ur_manipulator, gripper), named poses
    │                                     (including the pick-and-place stages of
    │                                     Stage_values.md), allowed collisions between robot links
    ├── srdf/robotiq_2f_140.xacro         gripper part of the SRDF: named states open (0.07),
    │                                     close (0.63) and grasp_cube (0.265, closed around the
    │                                     80 mm cube), no collision checking for the contact pads
    └── config/
        ├── controllers.yaml              controllers that execute MoveIt trajectories
        ├── kinematics.yaml               IK solver (KDL)
        ├── ompl_planning.yaml            OMPL planner settings
        ├── joint_limits.yaml             velocity and acceleration limits
        └── pilz_cartesian_limits.yaml    velocity limits for straight-line motions
```

## Standalone start

Start MoveIt separately only if `bringup.launch.py` was started without `moveit:=True` and without
`moveit_rviz:=True`:

```bash
ros2 launch neo_ur_moveit_config neo_ur_moveit.launch.py \
    ur_type:=ur10 my_robot:=mpo_700 prefix:=ur10 use_gazebo:=true use_sim_time:=true
```

| Option | Default | Description |
| --- | --- | --- |
| `use_gazebo` | `false` | Set `true` in simulation: use the Gazebo robot description and controllers |
| `use_sim_time` | `false` | Set `true` in simulation |
| `launch_rviz` | `true` | Open the MoveIt RViz window (also allows manual planning) |
| `ur_type`, `prefix`, `my_robot`, `gripper` | `ur10`, `ur10`, `mpo_700`, `2f_140` | Robot variant |

Neobotix documentation: <https://neobotix-docs.de/ros/packages/neo_ur_moveit_config.html>
