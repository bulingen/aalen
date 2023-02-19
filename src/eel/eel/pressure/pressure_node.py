#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import math
from eel_interfaces.msg import PressureStatus
from ..utils.constants import SIMULATE_PARAM
from ..utils.topics import PRESSURE_STATUS, IMU_STATUS
from eel_interfaces.msg import ImuStatus

PUBLISH_FREQUENCY = 5


def calculate_depth_diff(pitch):
    return 0.375 * math.sin(pitch)

def calculate_center_depth_USE_THIS(main_depth, pitch):
    if pitch > 0:
        return main_depth - calculate_depth_diff(pitch)
    else:
        return main_depth + calculate_depth_diff(pitch)


def get_pressure_sensor(should_simulate: bool, parent_node: Node):
    if should_simulate:
        from .pressure_sim import PressureSensorSimulator

        return PressureSensorSimulator(parent_node=parent_node)
    else:
        from .pressure_sensor import PressureSensor

        return PressureSensor(parent_node=parent_node)


class PressureNode(Node):
    def __init__(self):
        super().__init__("pressure_node")
        self.declare_parameter(SIMULATE_PARAM, False)
        self.should_simulate = self.get_parameter(SIMULATE_PARAM).value

        self.sensor = get_pressure_sensor(self.should_simulate, self)

        self.current_pitch = 0.0

        self.create_subscription(ImuStatus, IMU_STATUS, self.handle_imu_msg, 10)


        self.publisher = self.create_publisher(PressureStatus, PRESSURE_STATUS, 10)
        self.updater = self.create_timer(1.0 / PUBLISH_FREQUENCY, self.publish_status)

        self.get_logger().info(
            "{}Pressure node started.".format(
                "SIMULATE " if self.should_simulate else ""
            )
        )

    def handle_imu_msg(self, msg):
        self.current_pitch = msg.pitch

    def publish_status(self):
        try:
            current_depth = self.sensor.get_current_depth()
            msg = PressureStatus()
            msg.depth = current_depth
            # if self.should_simulate:
            #     msg.depth = current_depth
            # else:
            #     msg.depth = calculate_center_depth_USE_THIS(current_depth, self.current_pitch)
            self.publisher.publish(msg)
        except (OSError, IOError) as err:
            self.get_logger().error(str(err))


def main(args=None):
    rclpy.init(args=args)
    node = PressureNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
