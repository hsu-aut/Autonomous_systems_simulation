# neo_sim_objects

This package places objects, such as a cube on a table, in the running Gazebo
simulation, or returns them to their start position.

| Property | Value |
| --- | --- |
| Origin | This project |
| Type | ROS 2 node (Python), launch file, configuration |
| Started by | Manual start (see [Usage](#usage)), or the launch file of an application |
| Configuration | `config/objects.yaml` |

## Data flow

```text
                       ┌─────────────────────────┐
                       │ spawn_objects           │──▶ /get_model_list
config/objects.yaml ──▶│ (runs once, then exits) │──▶ /spawn_entity
                       │                         │──▶ /gazebo/set_entity_state
                       └─────────────────────────┘
```

- `/get_model_list` returns the objects that already exist in Gazebo.
- `/spawn_entity` adds an object that does not exist yet.
- `/gazebo/set_entity_state` returns an existing object to its start position. The object is not
  deleted and added again: a fast delete and re-add of the same name can remove the new object.
- The node exits with code 0 when all objects are in place, otherwise with code 1.

## Files

```text
neo_sim_objects/
├── neo_sim_objects/spawn_objects.py   node source (runs once, then exits)
├── config/objects.yaml                object definitions (each setting documented in the file)
├── launch/spawn_objects.launch.py     starts the node with config/objects.yaml
└── models/                            SDF files for objects other than boxes
```

## Object definition

Each entry in `objects.yaml` requires:

- `position: [x, y, z]`, optionally `yaw`
- either `size: [x, y, z]` (a box with high-friction contact settings is generated) or
  `model: <file.sdf>`

## Usage

```bash
# Place the objects defined in config/objects.yaml
ros2 launch neo_sim_objects spawn_objects.launch.py

# Place the objects defined in a custom file
ros2 launch neo_sim_objects spawn_objects.launch.py objects:=/full/path/to/my_objects.yaml
```

To place a single object from the command line:

```bash
ros2 run neo_sim_objects spawn_objects --ros-args -p objects:="[box2]" \
    -p box2.size:="[0.05, 0.2, 0.1]" -p box2.position:="[-4.668, -4.2, 0.825]"
```
