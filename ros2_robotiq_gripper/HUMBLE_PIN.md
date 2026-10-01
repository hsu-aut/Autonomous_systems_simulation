# Why `robotiq_driver` and `robotiq_controllers` are at an older commit

Upstream commit `a41ca0e` (#108) moved these two packages to the Rolling
ros2_control API (`HardwareComponentInterfaceParams`, `get_optional`), which
Humble does not have. The `humble` branch carries the same change.

They are checked out from `0230e84`, the last commit before it:

    git checkout 0230e84 -- robotiq_driver robotiq_controllers

`robotiq_description` stays at `main` — the 2F-140 macro there is what
`neo_simulation2` is written against, and it is unchanged between the two.

Do not `git checkout main -- .` in this directory; it will silently reintroduce
the build break. See [GRIPPER_INTEGRATION.md](GRIPPER_INTEGRATION.md), Addendum A2.
