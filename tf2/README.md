# tf2

This package is the core transform library of ROS 2 (`tf2`), version 0.25.24. It replaces the
`tf2` installed by `apt`, which is older and contains a deadlock that freezes Nav2.

| Property | Value |
| --- | --- |
| Origin | Third-party: [ros2/geometry2](https://github.com/ros2/geometry2), tag `0.25.24` (commit `404b722`), package `tf2` |
| Type | C++ library |
| Used by the simulation | Yes: every node built against `tf2` (Nav2, MoveIt, Gazebo plugins, this workspace) loads this library when the workspace is sourced |
| Temporary | Yes, see [When to remove it](#when-to-remove-it) |

## Why it is here

`tf2` 0.25.23 and older contains a deadlock between `waitForTransform` and
`testTransformableRequests`. When a laser scan in a Nav2 costmap waits for a transform at the moment
that transform arrives, the scan filter and the TF listener of the costmap block each other forever.
In `controller_server` (or `planner_server`) the TF data then stops updating: Nav2 goals end without
the robot moving (`Transform data too old when converting from map to odom`), RViz drops messages in
the `odom` frame, and the node does not stop on Ctrl-C. In tests this affected about every second
start.

`tf2` 0.25.24 fixes it ("Fix ABBA deadlock between `waitForTransform` and
`testTransformableRequests`", see [CHANGELOG.rst](CHANGELOG.rst)). At the time of writing, `apt`
still offers 0.25.23.

The build command in [Installation.md](../Installation.md#5-build-the-workspace) contains
`--allow-overriding tf2`, so that this package is used instead of the installed one.

## Changes to the original

Only one: [CMakeLists.txt](CMakeLists.txt) builds the tests only if `ament_cmake_google_benchmark`
is installed. It is not part of the simulation's dependencies, and without the change the build
fails. The library itself is unchanged.

## When to remove it

When `apt-cache policy ros-humble-tf2` shows version 0.25.24 or newer:

1. Update with `sudo apt update && sudo apt upgrade`.
2. Delete this folder and, in the workspace folder, `build/tf2` and `install/tf2`.
3. Remove `tf2` after `--allow-overriding` in the build command, and rebuild.

## Files

```text
tf2/
├── include/, src/          library (unchanged)
├── test/                   tests of the original (built only with ament_cmake_google_benchmark)
├── CMakeLists.txt          build file (changed, see above)
├── LICENSE                 BSD 3-Clause license of geometry2
└── README.upstream.md      original README
```
