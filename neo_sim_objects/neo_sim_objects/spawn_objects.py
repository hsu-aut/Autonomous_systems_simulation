#!/usr/bin/env python3
"""Put objects into the Gazebo world, or move them back to their start pose.

    ros2 launch neo_sim_objects spawn_objects.launch.py
    ros2 run neo_sim_objects spawn_objects --ros-args --params-file <objects.yaml>

The objects are listed in config/objects.yaml. Each one is either
  size: [x, y, z]   a box, generated here with the physics below, or
  model: <file>     an SDF file - a full path, or a file in this package's models/.

If an object already exists it is moved back to its start pose and stopped,
instead of being deleted and spawned again: Gazebo applies a delete a little later,
and a quick delete-then-spawn of the same name can remove the NEW object.

Afterwards the gripper's finger links (gripper_links in objects.yaml) and the objects
are set not to collide with each other, see OBJECT_MASK.

Exits 0 when every object is in place, 1 otherwise.
"""

import math
import os
import sys
import time

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from gazebo_msgs.srv import GetModelList, SetEntityState, SpawnEntity
from geometry_msgs.msg import Pose
from neo_link_attacher.srv import SetCollideBitmask

DEFAULT_MASS = 0.2                        # kg
DEFAULT_COLOR = [0.90, 0.30, 0.18]        # red, green, blue (0 to 1)

# Collision bitmasks, set through neo_link_attacher. Two collisions touch only when the
# AND of their masks is non-zero; Gazebo's default is 0xFFFF. With the objects at 0x0001
# and the finger links at 0xFFFE, fingers and objects pass through each other, while
# both still collide with everything else (table, floor). The simulated fingers move
# kinematically: closing on an object that is not exactly centred, the first finger
# hits it at full speed and Gazebo throws it off the table (measured: 9 mm off centre
# is enough). The object is held by neo_link_attacher's attach instead.
OBJECT_MASK = 0x0001
GRIPPER_MASK = 0xFFFE

# A box. The surface values matter more than the shape: Gazebo tends to shoot
# objects out from between gripper fingers, and these are the usual remedy -
#   mu / mu2 = 1.5    rubber-on-plastic friction
#   max_vel  = 0      no bounce-out velocity when a contact is resolved
#   min_depth= 0.001  1 mm of penetration before a corrective push, against jitter
#   kp / kd           a slightly soft contact, against impulse spikes
# The link is called "link": attach requests (neo_link_attacher) refer to it by that name.
BOX_SDF = """<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="{name}">
    <link name="link">
      <inertial>
        <mass>{mass}</mass>
        <inertia>
          <ixx>{ixx:.6e}</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>{iyy:.6e}</iyy><iyz>0</iyz>
          <izz>{izz:.6e}</izz>
        </inertia>
      </inertial>
      <collision name="collision">
        <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
        <surface>
          <friction><ode><mu>1.5</mu><mu2>1.5</mu2></ode></friction>
          <contact>
            <ode><kp>1000000.0</kp><kd>100.0</kd><max_vel>0.0</max_vel><min_depth>0.001</min_depth></ode>
          </contact>
        </surface>
      </collision>
      <visual name="visual">
        <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
        <material>
          <ambient>{ambient} 1</ambient>
          <diffuse>{diffuse} 1</diffuse>
          <specular>0.2 0.2 0.2 1</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>
"""


def box_sdf(name, size, mass, color):
    """SDF for a solid box of the given size (m), mass (kg) and colour."""
    sx, sy, sz = size
    return BOX_SDF.format(
        name=name, mass=mass, sx=sx, sy=sy, sz=sz,
        ixx=mass * (sy * sy + sz * sz) / 12.0,
        iyy=mass * (sx * sx + sz * sz) / 12.0,
        izz=mass * (sx * sx + sy * sy) / 12.0,
        diffuse=' '.join('%.2f' % c for c in color),
        ambient=' '.join('%.2f' % (0.95 * c) for c in color))


class ObjectSpawner(Node):

    def __init__(self):
        # Object settings are nested under each object's name (cube.size, ...), so
        # they are taken from the parameter file as they are, not declared one by one.
        super().__init__('spawn_objects', automatically_declare_parameters_from_overrides=True)
        self.reset = self.param('reset', True)
        self.names = list(self.param('objects', []))
        self.gripper_model = self.param('gripper_model', 'mpo_700')
        self.gripper_links = list(self.param('gripper_links', []))
        self.list_cli = self.create_client(GetModelList, '/get_model_list')
        self.spawn_cli = self.create_client(SpawnEntity, '/spawn_entity')
        self.set_state_cli = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        self.mask_cli = self.create_client(SetCollideBitmask, '/link_attacher/set_collide_bitmask')

    def param(self, name, default):
        return self.get_parameter(name).value if self.has_parameter(name) else default

    # ------------------------------------------------------------------ helpers
    def call(self, client, request, timeout=10.0):
        """Call a service; the response, or None. Logs why when it fails."""
        if not client.wait_for_service(timeout_sec=15.0):
            self.get_logger().error('%s not available - is Gazebo running '
                                    '(bringup.launch.py)?' % client.srv_name)
            return None
        fut = client.call_async(request)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=timeout)
        if fut.result() is None:
            self.get_logger().error('%s did not answer' % client.srv_name)
        return fut.result()

    def models(self):
        """Names of the models Gazebo has now, or None."""
        res = self.call(self.list_cli, GetModelList.Request(), timeout=2.0)
        return None if res is None or not res.success else list(res.model_names)

    def wait_until_present(self, name, timeout=10.0):
        """/spawn_entity returns once Gazebo has accepted the request; the object
        exists a little later. Wait for that, so nothing looks for it too early."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if name in (self.models() or []):
                return True
            time.sleep(0.1)
        return False

    def spec(self, name):
        """This object's settings, or (None, reason)."""
        position = self.param(name + '.position', None)
        if position is None or len(position) != 3:
            return None, 'needs "position: [x, y, z]"'
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = (float(v) for v in position)
        yaw = float(self.param(name + '.yaw', 0.0))
        pose.orientation.z, pose.orientation.w = math.sin(yaw / 2.0), math.cos(yaw / 2.0)

        size = self.param(name + '.size', None)
        model = self.param(name + '.model', None)
        if size is not None:
            if len(size) != 3:
                return None, '"size" needs three values [x, y, z]'
            sdf = box_sdf(name, [float(v) for v in size],
                          float(self.param(name + '.mass', DEFAULT_MASS)),
                          [float(v) for v in self.param(name + '.color', DEFAULT_COLOR)])
        elif model is not None:
            path = model if os.path.isabs(model) else os.path.join(
                get_package_share_directory('neo_sim_objects'), 'models', model)
            if not os.path.isfile(path):
                return None, 'model file %s not found' % path
            with open(path) as f:
                sdf = f.read()
        else:
            return None, 'needs either "size: [x, y, z]" or "model: <sdf file>"'
        return (pose, sdf), None

    # --------------------------------------------------------------------- main
    def run(self):
        log = self.get_logger()
        if not self.names:
            log.error('no objects configured - use "ros2 launch neo_sim_objects '
                      'spawn_objects.launch.py", or pass a file like config/objects.yaml')
            return 1
        present = self.models()
        if present is None:
            return 1

        ok = True
        placed = []
        for name in self.names:
            spec, why = self.spec(name)
            if spec is None:
                log.error('"%s": %s' % (name, why))
                ok = False
                continue
            pose, sdf = spec
            if name not in present:
                done = self.spawn(name, pose, sdf)
            elif self.reset:
                done = self.move_back(name, pose)
            else:
                log.info('"%s" already exists; leaving it where it is' % name)
                done = True
            ok &= done
            if done:
                placed.append(name)
        if placed and self.gripper_links:
            self.separate_from_gripper(placed)
        return 0 if ok else 1

    def spawn(self, name, pose, sdf):
        req = SpawnEntity.Request(name=name, xml=sdf, initial_pose=pose,
                                  reference_frame='world')
        res = self.call(self.spawn_cli, req, timeout=20.0)
        if res is None or not res.success:
            self.get_logger().error('could not spawn "%s"%s'
                                    % (name, '' if res is None else ': ' + res.status_message))
            return False
        if not self.wait_until_present(name):
            self.get_logger().error('"%s" was accepted but never appeared' % name)
            return False
        self.get_logger().info('spawned "%s" at x=%.3f y=%.3f z=%.3f'
                               % (name, pose.position.x, pose.position.y, pose.position.z))
        return True

    def move_back(self, name, pose):
        """Put an existing object back at its start pose, at rest."""
        req = SetEntityState.Request()
        req.state.name = name
        req.state.pose = pose                  # twist left at zero: at rest
        req.state.reference_frame = 'world'
        res = self.call(self.set_state_cli, req)
        if res is None or not res.success:
            self.get_logger().error('could not move "%s" back' % name)
            return False
        self.get_logger().info('moved "%s" back to x=%.3f y=%.3f z=%.3f'
                               % (name, pose.position.x, pose.position.y, pose.position.z))
        return True

    def separate_from_gripper(self, names):
        """Stop the gripper's finger links and these objects from colliding (OBJECT_MASK).

        Only a warning when it fails: the objects are in place either way."""
        log = self.get_logger()
        if not self.mask_cli.wait_for_service(timeout_sec=2.0):
            log.warning('%s not available (world without neo_link_attacher) - the gripper '
                        'fingers still collide with the objects' % self.mask_cli.srv_name)
            return
        targets = ([(name, '', OBJECT_MASK) for name in names] +
                   [(self.gripper_model, link, GRIPPER_MASK) for link in self.gripper_links])
        failed = 0
        for model, link, mask in targets:
            res = self.call(self.mask_cli, SetCollideBitmask.Request(model=model, link=link, bitmask=mask))
            if res is None or not res.ok:
                failed += 1
                log.warning('collision mask of %s/%s not set%s'
                            % (model, link or '*', '' if res is None else ': ' + res.message))
        if not failed:
            log.info('the fingers of "%s" do not collide with %s'
                     % (self.gripper_model, ', '.join('"%s"' % n for n in names)))


def main(args=None):
    rclpy.init(args=args)
    node = ObjectSpawner()
    try:
        rc = node.run()
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(rc)


if __name__ == '__main__':
    main()
