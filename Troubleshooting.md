# Troubleshooting

Look for your problem in the tables below: the left column describes what you see, the right column
what to do. Many problems have the same cause, a simulation that is still running in the background,
so try the [first steps](#1-first-steps) before anything else.

## Contents

1. [First steps](#1-first-steps)
2. [Installation and build](#2-installation-and-build)
3. [Starting the simulation](#3-starting-the-simulation)
4. [Navigation and MoveIt](#4-navigation-and-moveit)
5. [Messages you can ignore](#5-messages-you-can-ignore)

---

## 1. First steps

1. Stop everything:

   ```bash
   ros2 run neo_simulation2 stop_sim.sh
   ```

   Then check that `ros2 node list` prints nothing.
2. Check the terminal settings:

   ```bash
   echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID    # must print: rmw_cyclonedds_cpp 73
   ```

   If it prints something else, run `source ~/.bashrc` or open a new terminal.
3. Start the simulation again.

## 2. Installation and build

| Problem | Cause | Solution |
| --- | --- | --- |
| `colcon build` fails with `Could not find a package configuration file provided by "..."` | A ROS 2 package is not installed. | Repeat [installation step 3](Installation.md#3-install-the-dependencies). |
| `RMW implementation 'rmw_cyclonedds_cpp' ... not found` | Cyclone DDS is not installed. | Repeat [installation step 3](Installation.md#3-install-the-dependencies). |
| `Package '...' not found` when you start the simulation | The terminal was opened before the installation was finished, or before the last build added the package. | Run `source ~/.bashrc`, or open a new terminal. |

## 3. Starting the simulation

| Problem | Cause | Solution |
| --- | --- | --- |
| `Address already in use`, or Gazebo does not start | A previous Gazebo server is still running. | Run `ros2 run neo_simulation2 stop_sim.sh`, then start again. |
| The first start pauses for a long time | Gazebo downloads 3D models that are not part of the repository. | Wait. Internet access is needed once. |
| The Gazebo window shows no robot and no room | The window opened before the world was loaded. | Run `gzclient` in another terminal; this opens a new Gazebo window. Do not restart the simulation. |
| The arm does not move; the controllers do not start | Text in the robot description breaks the controller setup. | Run `python3 src/neo_simulation2/scripts/check_urdf_for_ros2_control.py`; it shows where the text is. |
| `ros2 node list` or `ros2 topic list` in another terminal does not show the running simulation | That terminal uses different middleware settings or a different domain ID than the simulation. | Check `echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID`, set the variables from [installation step 7](Installation.md#7-configure-the-ros-2-middleware), then run `ros2 daemon stop`. |
| The computer runs slowly | Too many windows are open. | With `moveit:=True`, add `moveit_rviz:=False` (see [common combinations](Launch_arguments.md#3-common-combinations)). |

## 4. Navigation and MoveIt

| Problem | Cause | Solution |
| --- | --- | --- |
| `unknown goal response`, `unknown result response` (Nav2 or MoveIt); `Failed to change state for node: map_server` | Nodes of an earlier simulation are still running, so every node exists twice and the wrong one answers. | Run `ros2 run neo_simulation2 stop_sim.sh`, check with `ros2 node list` that no node is left, then start again. |
| Nav2 rejects goals or does not respond; `Failed to send goal response` in the log; `neo_localization2_node`: `"odom" passed to lookupTransform argument target_frame does not exist` | The simulation runs on Fast DDS, which loses messages while the nodes start. | Configure Cyclone DDS ([installation step 7](Installation.md#7-configure-the-ros-2-middleware)) and restart the simulation. |
| Nav2 reports errors about the `odom` frame | Navigation was started before the simulation. | Start the simulation first. |
| A node reports that `/compute_ik` or `/move_action` is not available | MoveIt was not started, or the node started before MoveIt was ready. | Start the simulation with `moveit:=True` (MoveIt is off by default). If you did, wait until the start-up has finished (about 40 s, see the [start-up sequence](neo_simulation2/README.md#start-up-sequence)), then start the node again. |
| MoveIt goals fail with `MoveIt error -4` and the warning `more than one action server` | MoveIt was started twice. | `bringup.launch.py moveit:=True` already starts MoveIt. Do not also start `neo_ur_moveit.launch.py`. |
| MoveIt: `Failed to initialize planning pipeline 'pilz_industrial_motion_planner'` | The Pilz planner is not installed. | Repeat [installation step 3](Installation.md#3-install-the-dependencies). |

## 5. Messages you can ignore

These messages appear in every run. They look like errors, but they do not indicate a fault.

| Message | Explanation |
| --- | --- |
| `No 3D sensor plugin(s) defined for octomap updates`, `Resolution not specified for Octomap` | MoveIt has no depth camera. Objects are added to its planning scene through `/apply_planning_scene` instead. |
| `Parameter 'hold_joints' has already been declared` | The arm and the gripper each have their own controller configuration block. |
| `The root link base_link has an inertia specified in the URDF` | Informational message of the URDF parser. |
| `No goal checker was specified in parameter 'current_goal_checker'` | Nav2 uses its only configured goal checker. |
| `[Deprecated]: "allow_nonzero_velocity_at_trajectory_end"`, `Mapping from 'position' to interface ...` | Informational messages of the arm controllers. |
| RViz `GL_INVALID_VALUE`, `/recognize_objects not available` | A graphics driver message, and a MoveIt RViz feature that is not used. |
| After `stop_sim.sh`: `port 11345 still held (TIME_WAIT)`, `[ros2run]: Process exited with failure 1` | All programs are stopped; the network port is released within about 30 s. Wait before the next start. |
| After Ctrl-C or `stop_sim.sh`: `process has died` (RViz, monitor, `move_group`) with exit code -11 or -6 | MoveIt and RViz crash while they clean up on exit. Their work is already done at that point. |
