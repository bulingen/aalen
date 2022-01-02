from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()
    
    gnss_node = Node(
        package="aalen",
        executable="gnss",
        name="gnss_node",
    )

    imu_node = Node(
        package="aalen",
        executable="imu",
        name="imu_node",
    )

    radio_node = Node(
        package="aalen",
        executable="radio",
        name="radio_node",
    )

    ld.add_action(gnss_node)
    ld.add_action(imu_node)
    ld.add_action(radio_node)
    
    return ld