from __future__ import annotations
from datetime import datetime
import simpy
from simpy.core import SimTime


class QEnvironment(simpy.Environment):
    def __init__(self, simulation_period: str, initial_time: SimTime = 0):
        super().__init__(initial_time)
        self.simulation_period = simulation_period

    def sim_timestamp(self, offset: int | float = 0) -> int:
        """
        Calculates the real-world timestamp w.r.t. simulation period in milliseconds based on the simulation period and current offset.
        Args:
            offset (int | float): The offset to apply to the simulation period's timestamp.
        Returns:
            int: The real-world timestamp in milliseconds.
        """

        return int(round(datetime.strptime(self.simulation_period, "%Y-%m-%d %H:%M:%S").timestamp() + offset, 2)) * 1000
