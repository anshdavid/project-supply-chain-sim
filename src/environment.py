from __future__ import annotations
from datetime import datetime
import simpy
from simpy.core import SimTime


class QEnvironment(simpy.Environment):
    def __init__(self, simulation_period: str, initial_time: SimTime = 0):
        """
        Initializes the environment with a simulation period and an optional initial time.
        Args:
            simulation_period (str): The simulation period in ISO 8601 format (e.g., "YYYY-MM-DDTHH:MM:SSZ").
            initial_time (SimTime, optional): The initial simulation time. Defaults to 0.
        """

        super().__init__(initial_time)
        self.simulation_period = simulation_period
        self.simulation_period_timestamp = datetime.strptime(simulation_period, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    def now_timestamp(self, offset: int | float = 0) -> int:
        """
        Calculates the real-world timestamp w.r.t. simulation period in milliseconds based on the simulation period and current offset.
        """

        return int(round(self.simulation_period_timestamp + self.now + offset, 2)) * 1000
