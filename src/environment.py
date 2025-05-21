from __future__ import annotations
from datetime import datetime
import simpy
from simpy.core import SimTime


class QEnvironment(simpy.Environment):
    def __init__(self, simulation_period: str, initial_time: SimTime = 0):
        super().__init__(initial_time)
        self.simulation_period = simulation_period

    def get_timestamp_now(self) -> int:
        """
        Returns the current timestamp in milliseconds as an integer.

        The timestamp is calculated by converting the simulation period (assumed to be an ISO formatted string)
        to a datetime object, obtaining its Unix timestamp in seconds, multiplying by 1000 to convert to milliseconds,
        and then adding the current offset (`self.now`).

        Returns:
            int: The current timestamp in milliseconds.
        """

        def to_milint(x, y) -> int:
            stamp_ = datetime.fromisoformat(x).timestamp() + y
            return int(stamp_ * 1000)

        return to_milint(self.simulation_period, self.now)
