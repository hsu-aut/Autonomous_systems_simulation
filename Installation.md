# Installation

This guide sets up the simulation on your computer, step by step. You only need to do it once. When
you have finished, continue with [Running the simulation](README.md#1-running-the-simulation) in the
README.

New to ROS 2? The terms used here (workspace, package, build, source) are explained in
[Terminology.md](Terminology.md).

## Contents

1. [Requirements](#1-requirements)
2. [Install ROS 2 Humble](#2-install-ros-2-humble)
3. [Install the dependencies](#3-install-the-dependencies)
4. [Create the workspace and clone the repository](#4-create-the-workspace-and-clone-the-repository)
5. [Build the workspace](#5-build-the-workspace)
6. [Set up the terminal](#6-set-up-the-terminal)
7. [Configure the ROS 2 middleware](#7-configure-the-ros-2-middleware)
8. [Check the installation](#8-check-the-installation)

---

## 1. Requirements

| Item | Requirement |
| --- | --- |
| Operating system | Ubuntu 22.04 |
| ROS 2 | Humble, desktop installation (step 2) |
| Simulator | Gazebo Classic 11 (installed in step 3) |
| Network | Internet access for the installation and for the first start of the simulation: Gazebo then downloads several 3D models |

## 2. Install ROS 2 Humble

ROS 2 is the software framework the simulation is built on. Install it as described in the
[official installation guide](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html).
Choose the desktop variant, and also install the development tools:

```bash
sudo apt install ros-humble-desktop ros-dev-tools
```

## 3. Install the dependencies

The simulation needs further ROS 2 packages: Gazebo, the robot controllers, Nav2 (navigation),
MoveIt (arm motion planning), the keyboard control and Cyclone DDS (step 7). Install them all with one
command:

```bash
sudo apt install ros-humble-gazebo-ros-pkgs ros-humble-gazebo-ros2-control \
  ros-humble-ros2-control ros-humble-ros2-controllers \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox \
  ros-humble-moveit ros-humble-pilz-industrial-motion-planner ros-humble-moveit-servo \
  ros-humble-warehouse-ros-sqlite ros-humble-ur-description \
  ros-humble-xacro ros-humble-joint-state-publisher-gui ros-humble-teleop-twist-keyboard \
  ros-humble-rmw-cyclonedds-cpp xterm
```

You check that nothing is missing in step 4, once the repository is on your computer.

## 4. Create the workspace and clone the repository

The workspace is the folder in which the simulation is built: `neobotix_workspace` in your home
folder. The repository is downloaded ("cloned") into its subfolder `src`:

```bash
cd
mkdir neobotix_workspace
cd neobotix_workspace
git clone https://github.com/hsu-aut/Autonomous_systems_simulation.git src
```

All further commands in this documentation are run in this workspace folder, and all paths are given
relative to it.

**Check the dependencies.** `rosdep` compares the dependencies listed in the packages of the repository
with the software installed on your computer:

```bash
rosdep update
rosdep check --from-paths src --ignore-src --rosdistro humble -t buildtool -t build -t build_export -t exec
```

- It prints `All system dependencies have been satisfied`: everything is installed. Continue with
  step 5.
- It lists missing packages: install them with

  ```bash
  rosdep install --from-paths src --ignore-src --rosdistro humble -y -t buildtool -t build -t build_export -t exec
  ```

> **Note:** Two optional parts need packages that are neither available through `apt` nor part of this
> repository: the Elite arm models (`elite_description`) and the multi-robot RViz configuration
> `neo_nav2_bringup/rviz/multi_robot.rviz` (`neo_fleet`). The simulation uses neither of them, so you
> can ignore them.

## 5. Build the workspace

Building compiles the packages and installs them into the folder `install/`. In the workspace folder,
run:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --allow-overriding robotiq_description \
  --base-paths $(ls -d src/*/ | grep -v mpo_700_workspace)
```

The build has succeeded when the output ends with `Summary: <n> packages finished`. Compiler warnings
along the way are normal.

> **Important:** Always build in the workspace folder, and always with this command. Its options:
>
> - `--base-paths` leaves out the folder `src/mpo_700_workspace`, if it is present. That folder must not
>   be built in this workspace.
> - `--allow-overriding` lets the package `robotiq_description` of this repository replace the version
>   installed by `apt`.
> - `--symlink-install` links Python, YAML, launch and xacro files from `src/` instead of copying them.

**When to build again.** After you change files in `src/`:

| Change | Build again? |
| --- | --- |
| C++ source files (`.cpp`, `.hpp`) | Yes |
| Files added or deleted | Yes |
| Existing Python, YAML, launch or xacro files | No. Thanks to `--symlink-install`, the change takes effect at the next start. |

## 6. Set up the terminal

A terminal can only use ROS 2 and the built workspace after it has loaded ("sourced") their setup
files. To have this done automatically in every new terminal, add these two lines to the end of the
file `.bashrc` in your home folder:

```bash
source /opt/ros/humble/setup.bash
source ~/neobotix_workspace/install/setup.bash
```

`.bashrc` runs in whatever folder a terminal opens in, so the workspace is given relative to the home
folder (`~/`) here.

## 7. Configure the ROS 2 middleware

The middleware carries all messages between the ROS 2 programs. The simulation uses Cyclone DDS
instead of the default Fast DDS: Nav2 and MoveIt 2 recommend Cyclone DDS for ROS 2 Humble, and with
Fast DDS navigation and MoveIt goals can get lost.

Add these lines to the end of `.bashrc`, below the lines from step 6:

```bash
# DDS Implementation & variables sourcing
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" multicast="true"/></Interfaces></General></Domain></CycloneDDS>'
export ROS_DOMAIN_ID=73
```

| Variable | Function |
| --- | --- |
| `RMW_IMPLEMENTATION` | Selects Cyclone DDS as the middleware. |
| `CYCLONEDDS_URI` | Keeps all ROS 2 messages on this computer (the loopback network interface `lo`). Multicast, which Cyclone DDS uses to find the other programs, is switched off on this interface by default, so it is switched on here. |
| `ROS_DOMAIN_ID` | Separates this computer from other ROS 2 computers in the same network. Use a number between 1 and 101 that no other computer in your network uses. |

Then open a new terminal and run once:

```bash
ros2 daemon stop
```

This stops the ROS 2 background process, which still runs with the old settings; it restarts with
the new ones by itself.

## 8. Check the installation

Every new terminal now has ROS 2, the workspace and the middleware settings; you never have to enter
them by hand. Terminals that were already open keep their old settings: close them, or run
`source ~/.bashrc` once in each.

To check, open a new terminal and run:

```bash
echo $RMW_IMPLEMENTATION $ROS_DOMAIN_ID    # prints: rmw_cyclonedds_cpp 73
```

The installation is complete. Start the simulation as described in
[Running the simulation](README.md#1-running-the-simulation).
