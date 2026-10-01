#!/usr/bin/env python3
"""Simulation stand-in for the real robot's lidar post-processing.

On the MPO-700 each SICK S300 publishes lidar_N/scan; neo_scan_filter_node
(neo_sick_s300-2) crops it to lidar_N/scan_filtered, and two topic_tools relays
merge both filtered streams into <robot namespace>/scan
(neo_mpo_700-2/launch/bringup.launch.py).
Navigation and localization read those topics, so the simulation has to produce
the same ones for one navigation.yaml to serve both. Neither package is available
here, so this node does both jobs for one lidar. Run it in the lidar's namespace:

    ros2 run neo_simulation2 sim_scan_filter.py --ros-args -r __ns:=/lidar_1

Cropping copies neo_scan_filter_node exactly: the scan keeps its size and angles,
and every range outside the intervals is set to 0.0 (which consumers drop as below
range_min), rather than being trimmed.
"""

import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class SimScanFilter(Node):

    def __init__(self):
        super().__init__('neo_scan_filter_node')
        # Flat [lo, hi, lo, hi, ...] in radians. The default is the value in the
        # real robot's configs/lidar/sick/s300/s300_filter_{1,2}.yaml.
        self.declare_parameter('scan_intervals', [-2.27, 2.27])
        # The merged stream goes to "scan" in the robot's namespace, the parent of
        # this node's lidar_N namespace: /lidar_1 -> /scan, /robot1/lidar_1 ->
        # /robot1/scan. The robot's relays do the same (robot_namespace + "scan").
        # Set merged_topic to override, or merge to false to disable.
        self.declare_parameter('merge', True)
        self.declare_parameter('merged_topic', '')

        flat = list(self.get_parameter('scan_intervals').value)
        if len(flat) % 2:
            raise ValueError('scan_intervals needs an even number of values')
        self.intervals = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]

        qos = QoSProfile(depth=1)
        self.pub = self.create_publisher(LaserScan, 'scan_filtered', qos)
        merged = self.get_parameter('merged_topic').value
        if not merged:
            robot_ns = self.get_namespace().rstrip('/').rpartition('/')[0]
            merged = robot_ns + '/scan'
        if self.resolve_topic_name(merged) == self.resolve_topic_name('scan'):
            raise ValueError('merged topic %s is also the input; run this node in a '
                             'lidar namespace (-r __ns:=/lidar_1)' % merged)
        self.merged_pub = None
        if self.get_parameter('merge').value:
            self.merged_pub = self.create_publisher(LaserScan, merged, qos)
            self.get_logger().info('scan_filtered -> %s' % merged)
        self.create_subscription(LaserScan, 'scan', self.on_scan, qos_profile_sensor_data)

    def crop(self, scan):
        ranges = list(scan.ranges)
        n = len(ranges)
        stop = 0
        for lo, hi in self.intervals:
            if hi <= scan.angle_min or lo >= scan.angle_max:
                continue
            start = 0 if lo <= scan.angle_min else int((lo - scan.angle_min) / scan.angle_increment)
            for u in range(stop, start):
                ranges[u] = 0.0
            stop = n - 1 if hi >= scan.angle_max else int((hi - scan.angle_min) / scan.angle_increment)
        for u in range(stop, n):
            ranges[u] = 0.0
        scan.ranges = ranges
        return scan

    def on_scan(self, msg):
        if self.intervals:
            msg = self.crop(msg)
        self.pub.publish(msg)
        if self.merged_pub is not None:
            self.merged_pub.publish(msg)


def main():
    rclpy.init()
    node = SimScanFilter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)   # a second Ctrl-C during cleanup
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
