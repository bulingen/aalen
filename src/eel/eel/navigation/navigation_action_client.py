from collections import deque
from typing import Deque, List, Sequence, cast

import rclpy
from action_msgs.msg import GoalStatus
from std_msgs.msg import Bool
from rclpy.action import ActionClient
from rclpy.node import Node

from eel_interfaces.action import Navigate
from eel_interfaces.msg import NavigationStatus, NavigationMission, Coordinate
from ..utils.topics import (
    NAVIGATION_CMD,
    NAVIGATION_STATUS,
    NAVIGATION_LOAD_MISSION,
    NAVIGATION_SET_TARGET,
)
from ..utils.nav import (
    get_distance_in_meters,
)

TOLERANCE_IN_METERS = 5.0


def create_waypoint_goal(coordinate: Coordinate) -> Navigate.Goal:
    result = Navigate.Goal()
    result.next_coordinate = coordinate
    result.type = Navigate.Goal.TYPE_WAYPOINT
    result.optional_sync_time = []
    # TODO: depth should be dynamic
    result.next_coordinate_depth = [2.0]
    return result


def create_surface_goal(next_coordinate: Coordinate) -> Navigate.Goal:
    result = Navigate.Goal()
    result.next_coordinate = next_coordinate
    result.type = Navigate.Goal.TYPE_SURFACE_SYNC
    # TODO: I don't think this is used in server?
    result.optional_sync_time = [6.0]
    # TODO: bad name. since it is not used when surface
    result.next_coordinate_depth = []
    return result


MINIMUM_SYNC_DISTANCE_METERS = 15.0


def create_goals(coordinates: Sequence[Coordinate]) -> Deque[Navigate.Goal]:
    result: Deque[Navigate.Goal] = deque()
    for index, elem in enumerate(coordinates):
        result.append(create_waypoint_goal(elem))
        has_next = index < (len(coordinates) - 1)
        if has_next:
            next = coordinates[index + 1]
            distance_to_next = get_distance_in_meters(
                elem.lat, elem.lon, next.lat, next.lon
            )
            if distance_to_next >= MINIMUM_SYNC_DISTANCE_METERS:
                result.append(create_surface_goal(next))

        # if index < (len(coordinates) - 1):
        #     new_list.append(elem + list1[index + 1])
        # else:
        #     new_list.append(elem)

    # TODO: ska man ta bort sista sync:en också? när den ändå kör ytläge
    # TODO: även stöd för att köra i ytläge i början?
    if len(coordinates) > 2:
        result[-1].next_coordinate_depth = [0.0]

    return result


class NavigationActionClient(Node):

    def __init__(self):
        super().__init__("navigation_action_client", parameter_overrides=[])
        self.logger = self.get_logger()
        self._action_client = ActionClient(self, Navigate, "navigate")

        self.update_goals_subscriber = self.create_subscription(
            NavigationMission, NAVIGATION_LOAD_MISSION, self.set_mission, 10
        )

        # self.set_target_subscriber = self.create_subscription(
        #     Coordinate, NAVIGATION_SET_TARGET, self.set_goal, 10
        # )

        self.navigation_cmd_subscriber = self.create_subscription(
            Bool, NAVIGATION_CMD, self.handle_nav_cmd, 10
        )

        self.nav_publisher = self.create_publisher(
            NavigationStatus, NAVIGATION_STATUS, 10
        )

        self.goals: Deque[Navigate.Goal] = deque()
        # self.goals: List[Navigate.Goal] = []
        self.goal_handles = []
        self.goals_in_progress = False
        self.auto_mode = False

        self.logger.info("Navigation client started")

    def set_mission(self, msg: NavigationMission) -> None:
        """Takes a list of coordinates and converts them to a list of navigation goals."""
        coordinates = cast(List[Coordinate], msg.coordinate_list)

        if len(coordinates) == 0:
            self.goals.clear()
        else:
            self.goals = create_goals(coordinates)
            # for coordinate in coordinates:
            #     goal_msg = Navigate.Goal()
            #     goal_msg.lat = coordinate.lat
            #     goal_msg.lon = coordinate.lon

            #     self.goals.append(goal_msg)

        print("GOALS", self.goals)

        self.logger.info(f"Set mission with {len(self.goals)} coordinates.")

    # def set_goal(self, msg):
    #     """Method for inserting a new goal at the front of the goal queue."""
    #     self.cancel_goals_in_progress()

    #     goal_msg = Navigate.Goal()
    #     goal_msg.lat = msg.lat
    #     goal_msg.lon = msg.lon

    #     self.logger.info(f"New target recieved with lat: {msg.lat} and lon {msg.lon}")
    #     self.goals.appendleft(goal_msg)
    #     self.goals = [goal_msg] = self.goals
    #     self.start_mission()

    def handle_nav_cmd(self, msg):
        """Handler for nav cmd messages, either automode or manual as bool."""
        new_auto_mode = msg.data

        self.logger.info(f"Navigation mode command recieved:  {self.auto_mode}")

        if new_auto_mode == True and self.goals_in_progress:
            self.logger.info(
                "Goals already set and in progress, cancel auto mode and set new goals."
            )

        if (
            (new_auto_mode == True)
            and (len(self.goals) > 0)
            and not self.goals_in_progress
        ):
            self.logger.info(
                f"Mission started. Mission contains {len(self.goals)} goals."
            )
            self.start_mission()

        if (new_auto_mode == False) and self.goals_in_progress:
            self.logger.info(f"Cancelling goals in progress.")
            self.cancel_goals_in_progress()

        self.auto_mode = new_auto_mode

    def start_mission(self):
        """Method for starting the goal processing, used for starting the iteration."""
        self.send_goal(self.goals[0])
        self.goals_in_progress = True

    def cancel_goals_in_progress(self):
        """Method to cancel all the ongoing actions"""
        for handel in self.goal_handles:
            handel.cancel_goal_async()

        self.goal_handles = []
        self.goals_in_progress = False

    def goal_response_callback(self, future):
        """Call back for when client has sent a goal to the server, will be accepted / rejected"""
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.logger.warning("Goal server is unable to process goal")
            return

        self.logger.debug("Goal was accepted by server")
        self.goal_handles.append(goal_handle)

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """Call back method for when the action server reports that is has finished a goal."""
        status = future.result().status

        if status == GoalStatus.STATUS_SUCCEEDED:
            result = future.result().result
            # self.logger.info(
            #     f"Goal finished successfully, reached coordinate at lat: {result.lat} lon: {result.lon}"
            # )
            self.logger.info(f"Goal finished successfully")

            self.goals.popleft()

            if len(self.goals) == 0:
                self.logger.info(f"Finished mission, no more goals left.")
                self.goals_in_progress = False
            else:
                self.send_goal(self.goals[0])

        elif status == GoalStatus.STATUS_CANCELED:
            self.logger.info(f"Goal was cancelled")

    def feedback_callback(self, feedback):
        """Feed back message from action server sent once per second when action server gets a gps position."""
        nav_msg = NavigationStatus()
        nav_msg.auto_mode_enabled = self.auto_mode
        nav_msg.meters_to_target = feedback.feedback.distance_to_target
        nav_msg.tolerance_in_meters = TOLERANCE_IN_METERS
        coordinate = Coordinate()
        coordinate.lat = self.goals[0].next_coordinate.lat
        coordinate.lon = self.goals[0].next_coordinate.lon
        nav_msg.next_target = [coordinate]

        self.nav_publisher.publish(nav_msg)

    def send_goal(self, goal_msg):
        """Method for sending a goal to the action server, returns a goal handle from the server."""
        self.logger.debug(f"Waiting for action server...")
        self._action_client.wait_for_server()

        # self.logger.info(
        #     f"Sending goal request with lat: {goal_msg.lat} and lon: {goal_msg.lon}"
        # )
        self.logger.info(f"Sending goal request")

        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback
        )

        self._send_goal_future.add_done_callback(self.goal_response_callback)

        return self._send_goal_future


def main(args=None):
    rclpy.init(args=args)
    action_client = NavigationActionClient()
    rclpy.spin(action_client)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
