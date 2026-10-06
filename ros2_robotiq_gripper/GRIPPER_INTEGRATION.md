# Robotiq 2F-140 Gripper Integration — Problem & Solution

> **Background for maintainers.** This is a record of problems met while building the simulation and how
> each was solved. You do not need it to use the simulation; start with the [main README](../README.md).

**Target:** MPO-700 + UR10 arm + Robotiq 2F-140 gripper in **Gazebo Classic 11**, ROS 2 Humble
**Date:** 2026-09-10
**Launch command this document makes work:**

```bash
ros2 launch neo_simulation2 simulation.launch.py my_robot:=mpo_700 world:=neo_workshop arm_type:=ur10
```

---

## TL;DR

The single visible symptom was `package 'ur_description' not found`. Behind it were **seven independent
defects** (Problem 1 is the packaging, Problems 2–7 are the defects proper). All of them trace back to one root cause:

> `neo_simulation2`'s gripper support was written against **modern Gazebo**, but this workspace runs
> **Gazebo Classic** (EOL January 2025). Every dependency in the arm/gripper chain has since migrated,
> and the two ecosystems disagree on plugin names, macro signatures, mesh path resolution, and whether
> the physics engine enforces `<mimic>` joints.

Nothing was wrong with the UR10 arm itself — it was verified working in isolation early on.

---

## Contents

1. [Problem 1 — Missing packages](#problem-1--missing-packages)
2. [Problem 2 — Stale `robotiq_description` from apt](#problem-2--stale-robotiq_description-from-apt)
3. [Problem 3 — `sim_ignition` no longer exists](#problem-3--sim_ignition-no-longer-exists)
4. [Problem 4 — Wrong ros2_control hardware plugin](#problem-4--wrong-ros2_control-hardware-plugin)
5. [Problem 5 — Gripper meshes invisible to Gazebo](#problem-5--gripper-meshes-invisible-to-gazebo)
6. [Problem 6 — Linkage fell apart (mimic joints)](#problem-6--linkage-fell-apart-mimic-joints)
7. [Problem 7 — Gripper rendered all white](#problem-7--gripper-rendered-all-white)
8. [Complete list of changes](#complete-list-of-changes)
9. [Verification performed](#verification-performed)
10. [Known remaining noise (safe to ignore)](#known-remaining-noise-safe-to-ignore)
11. [Reproducing from a clean checkout](#reproducing-from-a-clean-checkout)
12. [Addendum — changes after 2026-09-10](#addendum--changes-after-2026-09-10)

---

## Problem 1 — Missing packages

### Symptom

```
[ERROR] [launch]: Caught exception in launch:
  PackageNotFoundError: "package 'ur_description' not found"
```

The launch aborted instantly. Running `navigation.launch.py` afterwards then produced a flood of

```
Invalid frame ID "odom" passed to canTransform argument target_frame - frame does not exist
```

### Diagnosis

The `odom` errors were **not a second bug**. Because the simulation never started, no robot existed,
so nothing published the `odom` transform. One root cause, two sets of error messages.

`arm_type:=ur10` makes `robots/mpo_700/mpo_700.urdf.xacro:52` include `components/arm/ur_arm.urdf.xacro`,
which calls `$(find ur_description)`. Auditing the whole include chain revealed **three** missing packages,
not one:

| Package | Needed for |
|---|---|
| `ros-humble-ur-description` | UR arm macro + `ur10` config files |
| `ros-humble-robotiq-description` | gripper, included unconditionally by `robotiq_gripper.urdf.xacro` |
| `ros-humble-gazebo-ros2-control` | provides `libgazebo_ros2_control.so` |

The third is easy to miss. `gz_ros2_control` and `ign_ros2_control` were already installed — but those
are for **modern** Gazebo. Gazebo Classic needs the differently-named `gazebo_ros2_control`.

### Fix

```bash
sudo apt update && sudo apt install -y \
  ros-humble-ur-description \
  ros-humble-robotiq-description \
  ros-humble-gazebo-ros2-control
```

---

## Problem 2 — Stale `robotiq_description` from apt

### Symptom

```
error: Invalid parameter "parent"
when instantiating macro: ur_to_robotiq
  (/opt/ros/humble/share/robotiq_description/urdf/ur_to_robotiq_adapter.urdf.xacro)
```

### Diagnosis

The apt package is an **old snapshot** of
[PickNikRobotics/ros2_robotiq_gripper](https://github.com/PickNikRobotics/ros2_robotiq_gripper).
Two incompatibilities with what `neo_simulation2` expects:

| Required by neo_simulation2 | apt `0.0.1` | upstream `main` |
|---|---|---|
| `robotiq_2f_140_macro.urdf.xacro` | absent — only ships `2f_85` | present |
| `ur_to_robotiq` with `parent` + `child` | takes `connected_to`, hardcodes child | `prefix parent child rotation` |

**The trap:** upstream never bumped the version number. Both the stale apt build and current `main`
report `0.0.1`, so `apt` gives no hint that it is out of date.

`neo_simulation2` is at commit `3dd4948` *"Adding Robotiq gripper to ur10 arm (#105)"* (Feb 2025) — the
very commit that introduced this dependency. There is no `.repos` file pinning the source, and the
Neobotix Classic-Gazebo docs page has been stripped of install instructions since they dropped Classic
support, so nothing indicated a source build was required.

### Fix

Source-build it into the workspace so the overlay shadows the apt copy (commands run in the workspace
folder):

```bash
cd src
git clone https://github.com/PickNikRobotics/ros2_robotiq_gripper.git

# only robotiq_description is needed; the others pull in serial-port deps and fail to build
touch ros2_robotiq_gripper/robotiq_driver/COLCON_IGNORE
touch ros2_robotiq_gripper/robotiq_controllers/COLCON_IGNORE
touch ros2_robotiq_gripper/robotiq_hardware_tests/COLCON_IGNORE

cd .. && colcon build --symlink-install \
  --packages-select robotiq_description \
  --allow-overriding robotiq_description
```

Verify the overlay won:

```bash
ros2 pkg prefix robotiq_description
# must print .../neobotix_workspace/install/robotiq_description, NOT /opt/ros/humble
```

---

## Problem 3 — `sim_ignition` no longer exists

### Symptom

```
error: Invalid parameter "sim_ignition"
when instantiating macro: robotiq_gripper (.../robotiq_2f_140_macro.urdf.xacro)
```

### Diagnosis

`neo_simulation2` passed `sim_ignition="true"`. Upstream renamed that argument to `sim_gazebo` when
Ignition was rebranded to Gazebo.

**This rename is a trap.** The new name suggests Gazebo Classic, but inspecting
`2f_140.ros2_control.xacro:28` shows `sim_gazebo` still selects:

```xml
<xacro:if value="${sim_gazebo}">
    <plugin>gz_ros2_control/GazeboSimSystem</plugin>   <!-- MODERN Gazebo -->
</xacro:if>
```

So there is **no upstream flag that produces the Classic plugin**. Simply renaming the argument would
have swapped one broken configuration for another. See Problem 4.

Confirmed that `sim_gazebo` affects *only* the ros2_control block — geometry and `<mimic>` tags are
emitted unconditionally, so dropping it costs no kinematics.

---

## Problem 4 — Wrong ros2_control hardware plugin

### Symptom

Before fixing, the generated URDF contained **two mutually incompatible** hardware plugins:

```
gazebo_ros2_control/GazeboSystem     <- Classic  (from the UR arm)
gz_ros2_control/GazeboSimSystem      <- modern   (from the gripper)
```

Under Classic, `libgazebo_ros2_control.so` loads every `<ros2_control>` block in the URDF. It cannot
resolve `gz_ros2_control/GazeboSimSystem`, so the `controller_manager` fails.

### Fix

Tell the upstream macro **not** to emit its ros2_control block, and hand-write a Classic-compatible one:

```xml
<xacro:robotiq_gripper name="robotiq_gripper" prefix=""
                       parent="neo_gripper_mount_link"
                       include_ros2_control="false">
    <origin xyz="0 0 0" rpy="0 0 -${pi / 2}"/>
</xacro:robotiq_gripper>

<ros2_control name="robotiq_gripper" type="system">
    <hardware>
        <plugin>gazebo_ros2_control/GazeboSystem</plugin>
    </hardware>
    ...
</ros2_control>
```

This keeps the third-party clone pristine — all Classic-specific glue lives in `neo_simulation2`,
where it belongs.

A controller was also required. `ur_controllers.yaml` had no gripper entry, so even with working
hardware nothing could drive the gripper. Added `position_controllers/GripperActionController`
plus a spawner in `gazebo_robot.launch.py`.

---

## Problem 5 — Gripper meshes invisible to Gazebo

### Symptom

```
[Err] [MeshShape.cc:64] Failed to find mesh file
      [model://robotiq_description/meshes/collision/2f_140/robotiq_2f_140_base_link.stl]
```

All the meshes existed on disk. This does **not** fail the launch — it logs as an error and the robot
spawns with missing geometry.

### Diagnosis

`gzserver.launch.py` builds `GAZEBO_MODEL_PATH` using `GazeboRosPaths.get_paths()`, which scans every
package's `package.xml` for a `<gazebo_ros gazebo_model_path="..."/>` export. **Only packages that
declare this export are added.**

- `neo_simulation2` exports `${prefix}/..` → its meshes resolve.
- `robotiq_description` (and `ur_description`) export nothing.
- No package under `/opt/ros/humble` exports the parent share directory either.

Result: `model://robotiq_description/...` could never resolve.

### Fix

Add the export to `src/ros2_robotiq_gripper/robotiq_description/package.xml`, then rebuild:

```xml
<export>
  <build_type>ament_cmake</build_type>
  <!-- Lets Gazebo Classic resolve model://robotiq_description/meshes/... -->
  <gazebo_ros gazebo_model_path="${prefix}/.." />
</export>
```

Verify:

```bash
python3 -c "
import sys; sys.path.insert(0,'/opt/ros/humble/lib/gazebo_ros')
from gazebo_ros_paths import GazeboRosPaths
m,_,_ = GazeboRosPaths.get_paths()
print('robotiq present:', any('robotiq' in e for e in m.split(':')))"
```

---

## Problem 6 — Linkage fell apart (mimic joints)

### Symptom

The gripper spawned and controllers activated, but the fingers rendered **splayed and disconnected**,
floating free of the linkage.

### Diagnosis

**Gazebo Classic does not enforce URDF `<mimic>` tags in physics.** Modern Gazebo does. Upstream's
xacro even documents the assumption:

> *"With Gazebo or Hardware, they handle mimic joints, so we only need this command interface activated"*

True for `gz_ros2_control`, false for Classic.

The hand-written ros2_control block (Problem 4) declared only `finger_joint`, trusting that comment.
The other five joints were therefore **free revolute joints with no actuation and no constraint** —
physics simply let them swing loose.

`gazebo_ros2_control` has its own mimic mechanism, confirmed by inspecting the shared library:

```bash
strings /opt/ros/humble/lib/libgazebo_hardware_plugins.so | grep -i mimic
# "Mimicked joint '" / "'is mimicking joint '" / "multiplier"
```

It requires each mimicking joint to be declared in the `<ros2_control>` block with `mimic` and
`multiplier` params.

### Fix

Multipliers were extracted from the generated URDF rather than guessed:

| Joint | Multiplier |
|---|---|
| `left_inner_knuckle_joint` | −1 |
| `left_inner_finger_joint` | +1 |
| `right_outer_knuckle_joint` | −1 |
| `right_inner_knuckle_joint` | −1 |
| `right_inner_finger_joint` | +1 |

Added via a small macro:

```xml
<xacro:macro name="robotiq_mimic_joint" params="name multiplier">
    <joint name="${name}">
        <param name="mimic">finger_joint</param>
        <param name="multiplier">${multiplier}</param>
        <command_interface name="position"/>
        <state_interface name="position"/>
        <state_interface name="velocity"/>
    </joint>
</xacro:macro>
```

Runtime confirmation:

```
gazebo_ros2_control: Joint 'left_inner_knuckle_joint' is mimicking joint 'finger_joint' with multiplier: -1
gazebo_ros2_control: Joint 'left_inner_finger_joint'  is mimicking joint 'finger_joint' with multiplier: 1
gazebo_ros2_control: Joint 'right_outer_knuckle_joint'is mimicking joint 'finger_joint' with multiplier: -1
gazebo_ros2_control: Joint 'right_inner_knuckle_joint'is mimicking joint 'finger_joint' with multiplier: -1
gazebo_ros2_control: Joint 'right_inner_finger_joint' is mimicking joint 'finger_joint' with multiplier: 1
```

---

## Problem 7 — Gripper rendered all white

### Symptom

Geometry and kinematics correct, but every gripper part rendered flat white.

### Diagnosis

Two causes combined:

1. **The 2F-140 visual meshes are `.stl`** — STL stores geometry only, no colour. (The wrist adapter
   is `.dae`, which *does* embed material — it was the one part that rendered black correctly.)
2. **The URDF materials are unnamed.** Every gripper link carries `<material name="">` with an rgba
   value. Gazebo Classic discards unnamed URDF materials, and does not read link colours from URDF
   at all — it needs an explicit `<gazebo reference="...">` block. The gripper had none.

With colour available from neither source, Ogre falls back to default white.

### Fix

Both Gazebo material forms were tested through `gz sdf -p` before choosing. The `<ambient>`/`<diffuse>`
form was selected over named materials (`Gazebo/FlatBlack`) because it reproduces the model's exact
rgba values instead of approximating from a limited palette.

| Links | Colour |
|---|---|
| base, outer/inner fingers, inner knuckles | `0.1 0.1 0.1` — near-black body |
| left/right outer knuckle | `0.792157 0.819608 0.933333` — aluminium blue-grey |

> **Note on fixed-joint lumping.** `sdformat` merges fixed-joint children into their parents, so
> `left_outer_finger`, the finger pads and `robotiq_140_base_link` do not exist as separate SDF links.
> Material extensions *do* propagate through this lumping (verified), but a colour set directly on a
> lumped-away link has no effect — the parent's colour wins. The finger pads therefore inherit the
> inner finger's black, which matches real Robotiq rubber pads. Explicit pad colours were removed
> rather than left in as dead code.

Verified in the SDF Gazebo actually consumes: **11 of 12 gripper visuals carry an explicit colour**;
the 12th is the `.dae` adapter, which supplies its own.

---

## Complete list of changes

### `neo_simulation2/components/arm/robotiq_gripper.urdf.xacro`

The main file. Changes:

- `sim_ignition="true"` → removed (Problem 3)
- `include_ros2_control="true"` → `"false"` **in the `use_gazebo` branch only** (Problem 4; see Addendum A2 —
  the real-robot branch keeps `"true"` so upstream emits `robotiq_driver`)
- Added Classic `<ros2_control>` block using `gazebo_ros2_control/GazeboSystem` (Problem 4)
- Added `finger_joint` with command range `0.0 … 0.7` matching the URDF limit
- Added `robotiq_mimic_joint` macro + 5 mimic joint declarations (Problem 6)
- Added `robotiq_gazebo_colour` macro + 9 colour assignments (Problem 7)
- Added the `grasp_tcp` / `grasp_tip` virtual frames (Addendum A1)
- Everything Gazebo-specific wrapped in `<xacro:if value="$(arg use_gazebo)">` (Addendum A2)

### `neo_simulation2/configs/ur_config/ur10/ur_controllers.yaml`

```yaml
# under controller_manager.ros__parameters:
    robotiq_gripper_controller:
      type: position_controllers/GripperActionController

# at file scope:
robotiq_gripper_controller:
  ros__parameters:
    default: true
    joint: finger_joint
    allow_stalling: true
    max_effort: 100.0
    stall_velocity_threshold: 0.001
    stall_timeout: 2.0
```

Two further changes to this file were made later and had not been recorded here:

```yaml
# joint_state_broadcaster restricted to the 7 real joints (position, velocity).
# gazebo_ros2_control registers every mimic joint as "<name>_mimic"; left on the
# default "publish everything", those names reach /joint_states, and MoveIt logs
# "Joint 'left_inner_finger_joint_mimic' not found in model" on every update.
joint_state_broadcaster:
  ros__parameters:
    joints: [ur10shoulder_pan_joint, ..., ur10wrist_3_joint, finger_joint]
    interfaces: [position, velocity]

# joint_trajectory_controller path tolerance 0.2 -> 1.0 rad per joint.
# At 0.2 the controller aborted mid-trajectory on 4 of 12 arm moves in Gazebo.
# 0.5 -> 5/12, 0.8 -> 3/12, 1.0 -> 10/12. goal tolerance stays 0.1 so final
# accuracy is still enforced.
    constraints:
      ur10shoulder_pan_joint: { trajectory: 1.0, goal: 0.1 }
      # ... same for the other five
```

### `neo_simulation2/launch/gazebo_robot.launch.py`

```python
    # The Robotiq 2F-140 gripper rides along with the UR arm on the same
    # controller_manager, so it needs its own spawner.
    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["robotiq_gripper_controller", "-c", "/controller_manager"],
    )
```

appended inside the existing `if robot_arm_type != '':` block, so it only spawns when an arm is used.

### `ros2_robotiq_gripper/robotiq_description/package.xml`

Added the `gazebo_ros` model-path export (Problem 5).

### Change footprint

```
neo_simulation2/components/arm/robotiq_gripper.urdf.xacro  | 83 ++++++++++++++++---
neo_simulation2/configs/ur_config/ur10/ur_controllers.yaml | 12 +++
neo_simulation2/launch/gazebo_robot.launch.py              |  9 ++
ros2_robotiq_gripper/robotiq_description/package.xml       |  2 +
```

---

## Verification performed

Validated with a headless `gzserver` run (no GUI), spawning the robot and all three controllers:

```
Successfully spawned entity [mpo_700]
Successful 'activate' of hardware 'ur10'
Successful 'activate' of hardware 'robotiq_gripper'
Configured and activated joint_state_broadcaster
Configured and activated joint_trajectory_controller
Configured and activated robotiq_gripper_controller

mimic joints registered: 5
mesh failures:           0
material errors:         0
```

A spawner reports *"Configured and activated"* only if the controller successfully claimed its
interfaces from the hardware — so this confirms the gripper genuinely drives `finger_joint`.

**Not verified:** rendered pixels and physical grasping behaviour. Validation was done against the
generated SDF and runtime logs, not the GUI. Mimic-joint grasping under contact in Classic can be
twitchy and may need physics tuning.

### Driving the gripper

```bash
ros2 action send_goal /robotiq_gripper/robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.7, max_effort: 100.0}}"
```

`0.0` = open, `0.7` = fully closed. The name is the real robot's; in simulation
`gripper_action_relay.py` serves it in front of `/robotiq_gripper_controller/gripper_cmd`,
which also still works.

### Launch order

`gazebo_robot.launch.py` must be fully up with the robot spawned **before** starting
`navigation.launch.py`, or the nav stack spams `odom` frame errors (see Problem 1).

---

## Known remaining noise (safe to ignore)

| Message | Cause |
|---|---|
| `Parameter 'hold_joints' has already been declared` | `gazebo_ros2_control` declares it once per `<ros2_control>` block; there are now two. Logged as ERROR but non-fatal — hardware activates fine immediately after. |
| `Missing model.config for /home/<user>/...` (~55 lines) | Stale paths in `.gazebo/gui.ini` (in the home folder) `[model_paths]`, added via the GUI's *Insert → Add Path*. Purely the Insert panel. Remove with `cd && sed -i '/^filenames=/d' .gazebo/gui.ini`. |
| `Missing model.config for .../share/../ament_index`, `colcon-core` (6 lines) | Side effect of the `gazebo_model_path="${prefix}/.."` exports. **Required** — removing them breaks mesh resolution. |
| `xterm ... exit code 2` on Ctrl-C | `teleop_twist_keyboard` exits non-zero on SIGINT and xterm propagates it. Teleop works normally during the run. |
| `gzclient: Assertion 'px != 0' failed` | Known Gazebo Classic crash on shutdown. |
| `kdl_parser: root link base_link has an inertia` | Pre-existing in the MPO-700 URDF. |
| `Found remap rule '~/out:=scan'. This syntax is deprecated` | neo_simulation2's Gazebo sensor plugins. |

---

## Reproducing from a clean checkout

```bash
# 1. system packages
sudo apt update && sudo apt install -y \
  ros-humble-ur-description \
  ros-humble-robotiq-description \
  ros-humble-gazebo-ros2-control

# 2. correct robotiq_description from source (starting in the workspace folder)
cd src
git clone https://github.com/PickNikRobotics/ros2_robotiq_gripper.git
touch ros2_robotiq_gripper/{robotiq_driver,robotiq_controllers,robotiq_hardware_tests}/COLCON_IGNORE

# 3. add the gazebo model-path export to
#    ros2_robotiq_gripper/robotiq_description/package.xml   (see Problem 5)

# 4. apply the neo_simulation2 changes  (see Complete list of changes)

# 5. build (back in the workspace folder)
cd ..
colcon build --symlink-install --allow-overriding robotiq_description

# 6. run
source install/setup.bash
export LC_NUMERIC=en_US.UTF-8
ros2 launch neo_simulation2 simulation.launch.py \
  my_robot:=mpo_700 world:=neo_workshop arm_type:=ur10
```

### Quick sanity check without launching

```bash
xacro src/neo_simulation2/robots/mpo_700/mpo_700.urdf.xacro \
      use_gazebo:=true arm_type:=ur10 use_docking_adapter:=False > check.urdf

# should print gazebo_ros2_control/GazeboSystem ONLY — no gz_ros2_control
grep -oP '(?<=<plugin>)[^<]+' check.urdf | sort -u
```

---

## Addendum — changes after 2026-09-10

These changes touch the same files. Recorded here so
this document stays the single account of the gripper integration.

### A1. Virtual grasp frames

Two massless links on fixed joints off `robotiq_140_base_link`, in `robotiq_gripper.urdf.xacro`:

| frame | offset along the approach axis | meaning |
|---|---|---|
| `grasp_tcp` | 0.1770 m | grasp centre — the midpoint between the pads with the gripper open. Motion targets are planned for this. |
| `grasp_tip` | 0.2357 m | fingertip extremity **with the gripper fully closed**. Nothing may be commanded that puts this below an obstacle. |

sdformat drops them from the SDF (no geometry, no inertia) so Gazebo never sees them; `robot_state_publisher`
still puts them on TF. They replace an earlier scheme that took the pad midpoint from live TF, which was
wrong twice: the pads swing on a four-bar linkage, so that midpoint drifts 23.7 mm as the fingers close; and
the pad frame origin is the *centre* of the pad face, 35 mm short of the fingertip. Commanding it onto the
centre of a 50 mm cube drove the fingertips 10 mm into the tabletop.

`grasp_tip` is measured closed, not open, because the fingertips sweep a further 23.7 mm outward as the
fingers shut. Sized on the open pose the clearance was consumed during the grasp itself and the fingers
stalled on the table at `finger_joint = 0.30` with the cube untouched between them.

Both numbers are derived from the URDF meshes.

### A2. Simulation / real-robot gating

`mpo_700.urdf.xacro` and `ur_arm.urdf.xacro` already switched on `use_gazebo`; this file did not, and
emitted `gazebo_ros2_control/GazeboSystem` unconditionally. With `use_gazebo:=false` the real robot would
have tried to load a Gazebo hardware plugin for the gripper. Now:

```
use_gazebo:=true   ros2_control robotiq_gripper -> gazebo_ros2_control/GazeboSystem         18 <gazebo> tags
use_gazebo:=false  ros2_control robotiq_gripper -> robotiq_driver/RobotiqGripperHardwareInterface   0 <gazebo> tags
```

The real path calls upstream's macro with `include_ros2_control="true"` and every sim flag off, plus a new
`gripper_com_port` xacro arg (default `/dev/ttyUSB0`). The grasp frames are emitted in both.

**The real-robot driver is now built** (2026-09-11). Two things were needed, and the second is the
one that will bite anyone repeating this:

1. `robotiq_driver` needs the `serial` package, which is not in apt for Humble. It was cloned from
   `tylerjw/serial` (`ros2` branch) into `src/serial` and is now included in this repository.

2. **Neither `main` nor upstream's `humble` branch builds on Humble.** Commit `a41ca0e` ("Fix all
   deprecation warnings", #108) moved `robotiq_driver` and `robotiq_controllers` to the Rolling
   ros2_control API — `HardwareComponentInterfaceParams`, `get_optional()`, bool-returning
   `set_value()` — none of which exist in Humble's `hardware_interface`. The `humble` branch has the
   same change. So those two packages are checked out from **`0230e84`**, the last commit before it,
   while `robotiq_description` stays at `main` (only 2F-85 files differ between the two, and the 2F-140
   macro is identical):

   ```bash
   cd src/ros2_robotiq_gripper
   git checkout 0230e84 -- robotiq_driver robotiq_controllers
   ```

   `git status` shows the two directories as staged modifications against `main`; that is intentional.
   `robotiq_hardware_tests` keeps its `COLCON_IGNORE`.

Verified: `pluginlib` lists `robotiq_driver::RobotiqGripperHardwareInterface`, which is exactly what the
`use_gazebo:=false` URDF names. Not verified: talking to a physical gripper — there is none here.

### A3. Force control was tried and reverted — do not retry without reading this

A plain `position` command interface makes `GazeboSystem` drive the joint with `SetPosition()`, a kinematic
teleport. Closing on a 100 mm cube the fingers sweep straight through it and the contact solver fires it
0.37 m across the table. That is real, and it is why a friction grasp does not work in this simulation.

`position_pid` (PID → `SetForce()`) is the principled fix and was tried. It does not survive this model's
numbers: finger link inertias are ~3×10⁻⁶ kg·m² and `neo_workshop.world` steps at 0.01 s. Any force large
enough to grip is enormous against that inertia — at a 10 N·m effort limit the joint gains 34 000 rad/s in a
single step and blows through its own end stop (`finger_joint` was observed at 2.55 rad against a 0.7 rad
limit, linkage torn apart on screen). Working back from stability instead, `kp` is capped around 3×10⁻⁴ and
yields no usable grip force. There is no window.

Making it viable would need finger inertias inflated ~3000× (to ~10⁻² kg·m², the standard Gazebo trick for
light gripper fingers) or a much smaller `max_step_size`. Until one of those is done, the grasp is secured
by attaching the object with a fixed joint once the fingers are on it, which is what
`gazebo_grasp_plugin` does and what most Gazebo Classic grasping setups rely on.

The full reasoning is in the comment block above the `<ros2_control>` element in `robotiq_gripper.urdf.xacro`.

### A4. Effort limits

`robotiq_description/urdf/robotiq_2f_140.xacro` was briefly patched from `effort="1000"` to `10.0` as part of
A3 and **reverted** with it. It is back at upstream's 1000 on all four finger joints. Its only other local
patch remains the `finger_joint` lower limit `0` → `-0.01` (Problem 6).

---

## Long-term note

`neo_simulation2`'s own README states that Gazebo Classic reached end-of-life in January 2025 and that
all Neobotix robots have been migrated to modern Gazebo. Every problem in this document stems from
running Classic against dependencies that have already moved on.

If the gripper becomes central to this project, the `fortress-migration` branch of `neo_simulation2`
targets modern Gazebo and avoids Problems 3, 4, 6 and 7 entirely.
