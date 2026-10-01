#!/usr/bin/env python3
"""Serve the gripper action under the real robot's name in simulation.

On the MPO-700 the Robotiq driver has its own controller_manager in namespace
robotiq_gripper (neo_mpo_700-2/configs/robotiq/robotiq_control.launch.py), so
the action is

    /robotiq_gripper/robotiq_gripper_controller/gripper_cmd

In Gazebo one gazebo_ros2_control controller_manager runs every controller, and
all of its controllers share its namespace, so the same controller appears as

    /robotiq_gripper_controller/gripper_cmd

This relays goals, feedback, results and cancels from the first name to the
second, so MoveIt's controllers.yaml and other clients can use the real name on
both targets.
"""

import signal
import threading
import time

import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from control_msgs.action import GripperCommand


class GripperActionRelay(Node):

    def __init__(self):
        super().__init__('gripper_action_relay')
        self.declare_parameter(
            'serve', '/robotiq_gripper/robotiq_gripper_controller/gripper_cmd')
        self.declare_parameter('forward_to', '/robotiq_gripper_controller/gripper_cmd')
        serve = self.get_parameter('serve').value
        forward_to = self.get_parameter('forward_to').value

        group = ReentrantCallbackGroup()
        self.client = ActionClient(self, GripperCommand, forward_to, callback_group=group)
        self.server = ActionServer(
            self, GripperCommand, serve,
            execute_callback=self.execute,
            goal_callback=lambda _goal: GoalResponse.ACCEPT,
            cancel_callback=lambda _handle: CancelResponse.ACCEPT,
            callback_group=group)
        self.get_logger().info('relaying %s -> %s' % (serve, forward_to))

    @staticmethod
    def wait(future, timeout):
        done = threading.Event()
        future.add_done_callback(lambda _f: done.set())
        return done.wait(timeout)

    def execute(self, goal_handle):
        if not self.client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('controller action server unavailable')
            goal_handle.abort()
            return GripperCommand.Result()

        send = self.client.send_goal_async(
            goal_handle.request,
            feedback_callback=lambda fb: goal_handle.publish_feedback(fb.feedback))
        if not self.wait(send, 5.0) or not send.result().accepted:
            goal_handle.abort()
            return GripperCommand.Result()
        inner = send.result()

        result_future = inner.get_result_async()
        cancel_sent = False
        while not result_future.done():
            if goal_handle.is_cancel_requested and not cancel_sent:
                inner.cancel_goal_async()
                cancel_sent = True
            time.sleep(0.02)

        wrapped = result_future.result()
        if wrapped.status == GoalStatus.STATUS_SUCCEEDED:
            goal_handle.succeed()
        elif wrapped.status == GoalStatus.STATUS_CANCELED and goal_handle.is_cancel_requested:
            goal_handle.canceled()
        else:
            goal_handle.abort()
        return wrapped.result


def main():
    rclpy.init()
    node = GripperActionRelay()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)   # a second Ctrl-C during cleanup
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
