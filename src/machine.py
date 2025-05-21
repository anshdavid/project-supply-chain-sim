"""
machine.py
----------
Defines the QMachine class and related utilities for simulating a production machine within a factory environment.

Features:
    - QMachine: Simulates a production machine, tracking operational state, production statistics, and logs.
    - QMachineConfig: Configuration schema for initializing a QMachine.
    - QMachineState: Tracks the current state and statistics of the machine, and provides methods for state and production updates.
    - Utility functions for operation/failure timing.

Usage:
    - Use QMachine.from_config() or QMachine.__init__() to create a machine.
    - Use produce_p() to start production of parts.
    - Use repair() to simulate repairs and restart() to resume operation after repair or failure.

Dependencies:
    - random: For stochastic time calculations.
    - pydantic: For configuration and state models.
    - src.environment.QEnvironment: The simulation environment.
    - src.factory.QFactory: The factory context (referenced via TYPE_CHECKING).
    - src.logs.QLogEntry: Base class for log entries.
"""

from __future__ import annotations

import random
import sys
from typing import Literal, TYPE_CHECKING

from ipywidgets import fixed
from pydantic import BaseModel, Field, PrivateAttr

from src.environment import QEnvironment
from src.logs import QLogEntry

if TYPE_CHECKING:
    from src.factory import QFactory


def calculate_timeout_to_failure(mttf: float | int, fixed_time: bool = False) -> float:
    """
    Calculate the time to the next failure event using the machine's mean time to failure (MTTF).

    Args:
        mttf (float | int): Mean time to failure.
        fixed_time (bool, optional): If True, use a fixed time. If False, sample from an exponential distribution.

    Returns:
        float: The calculated timeout duration until the next failure event.
    """
    if fixed_time:
        return mttf
    else:
        return random.expovariate(1 / mttf)


def calculate_timeout_to_produce(
    mean_operation_time: float | int, sigma: float | int, fixed_time: bool = False
) -> float:
    """
    Calculate the timeout required to produce a part.

    Args:
        mean_operation_time (float | int): Mean time per part.
        sigma (float | int): Standard deviation in operation time.
        fixed_time (bool, optional): If True, use a fixed time. If False, sample from a normal distribution.

    Returns:
        float: The calculated timeout value for producing a part.
    """
    if fixed_time:
        return mean_operation_time

    else:
        timeout_event_production = random.normalvariate(mean_operation_time, sigma)
        while timeout_event_production <= 0:
            timeout_event_production = random.normalvariate(mean_operation_time, sigma)

    return timeout_event_production


class QMachine:
    """
    Simulates a production machine within a factory environment.

    Responsibilities:
        - Tracks operational state, production statistics, and logs.
        - Handles state transitions, failures, repairs, and production events.
        - Integrates with a QFactory and QEnvironment.

    Inner Classes:
        QMachineConfig: Configuration schema for initializing a QMachine.
        QMachineState: Tracks the current state and statistics of the machine.

    Methods:
        from_config(env, config): Instantiate a QMachine from a configuration object.
        produce_p(parts_to_produce): Simulate the production of a specified number of parts.
        restart(): Restart the machine after a failure or repair.
        repair(timeout): Simulate the repair process.
    """

    class QMachineConfig(BaseModel):
        """
        Configuration schema for a QMachine.

        Attributes:
            name (str): Name of the machine.
            state (Literal): Current operational state ('idle', 'working', 'broken', 'repair').
            mean_operation_time (float): Mean time per part (must be > 0).
            sigma (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure (must be > 0).
        """

        name: str = Field(description="Name of the machine")
        state: Literal["idle", "working", "broken", "repair"] = Field(
            description="Current operational state: idle, working, broken"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(..., description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        fixed_time: bool = Field(default=True, description="Use fixed time for production and failure events")

    class QMachineState(BaseModel):
        """
        Represents the operational state and statistics of a machine.

        Attributes:
            name (str): Name of the machine.
            state (Literal): Current operational state ('idle', 'working', 'broken', 'repair').
            mean_operation_time (float): Mean time per part (must be > 0).
            sigma (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure (must be > 0).
            parts_produced (int): Total parts produced by the machine.
            parts_pending (int): Pending parts to be produced.
            logs (list[QLogEntry]): List of log entries for the machine.
            timeout_failure (float): Timeout event for failure.
            timeout_production (float): Timeout event for production.
        """

        name: str
        state: Literal["idle", "working", "broken", "repair"] = Field(
            description="Current operational state: idle, working, broken"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        parts_produced: int = Field(default=0, description="Total parts produced by the machine")
        parts_pending: int = Field(default=0, description="Pending parts to be produced")
        fixed_time: bool = Field(default=True, description="Use fixed time for production and failure events")

        logs: list[QLogEntry] = []

        timeout_failure: float = Field(default=0, description="Timeout event for failure")
        timeout_production: float = Field(default=0, description="Timeout event for production")

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)

        def set_state(self, state: Literal["idle", "working", "broken", "repair"]):
            """
            Set the state of the machine.

            Args:
                state (Literal["idle", "working", "broken", "repair"]): The new state to set for the machine.
            """
            self.state = state

        def get_state(self) -> str:
            """
            Get the current state of the machine.

            Returns:
                str: The current state.
            """
            return self.state

        def is_state(self, state: Literal["idle", "working", "broken", "repair"]) -> bool:
            """
            Check if the current state of the machine matches the specified state.

            Args:
                state (Literal["idle", "working", "broken", "repair"]): The state to compare against the machine's current state.

            Returns:
                bool: True if the machine's current state matches the specified state, False otherwise.
            """
            return self.state == state

        def update_parts_produced(self, parts: int):
            """
            Update the number of parts produced by the machine.

            Args:
                parts (int): The number of parts to add to the current total.
            """
            self.parts_produced += parts

        def update_parts_pending(self, parts: int):
            """
            Update the number of parts pending by adding the specified amount.

            Args:
                parts (int): Signed (+/-) number of parts to add or subtract to the pending count.
            """
            self.parts_pending += parts

        def set_timeout_to_failure(self, timeout: float):
            """
            Set the timeout for the next failure event.

            Args:
                timeout (float): The timeout duration to set.
            """
            self.timeout_failure = timeout

        def get_timeout_to_failure(self) -> float:
            """
            Get the timeout for the next failure event.

            Returns:
                float: The timeout duration for the next failure event.
            """
            return self.timeout_failure

        def set_timeout_to_produce(self, timeout: float):
            """
            Set the timeout for the next production event.

            Args:
                timeout (float): The timeout duration to set.
            """
            self.timeout_production = timeout

        def get_timeout_to_produce(self) -> float:
            """
            Get the timeout for the next production event.

            Returns:
                float: The timeout duration for the next production event.
            """
            return self.timeout_production

        def set_factory(self, factory: QFactory):
            """
            Set the factory for the machine.

            Args:
                factory (QFactory): The factory instance to associate with this machine.
            """
            self._factory = factory

        def get_factory(self) -> QFactory | None:
            """
            Get the associated QFactory instance if available.

            Returns:
                QFactory | None: The factory object associated with this instance, or None if not set.
            """
            return self._factory

        def set_environment(self, env: QEnvironment):
            """
            Set the environment for the machine.

            Args:
                env (QEnvironment): The environment instance to associate with this machine.
            """
            self._environment = env

        def get_environment(self) -> QEnvironment:
            """
            Get the current QEnvironment instance associated with the machine.

            Returns:
                QEnvironment: The environment object currently set for this machine.
            """
            return self._environment

    @classmethod
    def from_config(cls, env: QEnvironment, config: QMachineConfig):
        """
        Create a QMachine instance from the provided configuration.

        Args:
            env (QEnvironment): The environment in which the machine operates.
            config (QMachineConfig): Configuration object containing machine parameters.

        Returns:
            QMachine: An instance of QMachine initialized with the provided configuration.
        """
        return cls(
            name=config.name,
            env=env,
            mean_operation_time=config.mean_operation_time,
            sigma_operation=config.sigma,
            mttf=config.mttf,
        )

    def __init__(self, name: str, env: QEnvironment, mean_operation_time: float, sigma_operation: float, mttf: float):
        """
        Initialize a QMachine with the given parameters and set up its state and event timers.

        Args:
            name (str): Name of the machine.
            env (QEnvironment): The simulation environment.
            mean_operation_time (float): Mean time per part.
            sigma_operation (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure.
        """
        self.machine_state: QMachine.QMachineState = QMachine.QMachineState(
            name=name,
            state="idle",
            mean_operation_time=mean_operation_time,
            sigma=sigma_operation,
            mttf=mttf,
            parts_produced=0,
        )

        self.machine_state.set_environment(env)
        self.machine_state.set_state("idle")

        ttf = calculate_timeout_to_failure(self.machine_state.mttf, fixed_time=self.machine_state.fixed_time)
        self.machine_state.set_timeout_to_failure(ttf)
        self.event_failure = self.machine_state.get_environment().timeout(ttf)
        self.event_production = self.machine_state.get_environment().timeout(0)

    def produce_p(self, parts_to_produce: int):
        """
        Simulate the production of a specified number of parts by the machine.

        Args:
            parts_to_produce (int): The number of parts the machine should produce.

        Yields:
            dict: A dictionary indicating which event (production or failure) occurred.

        Behavior:
            - Sets the machine state to "working" and initializes the number of parts pending.
            - For each part to be produced:
                - Waits for either the production of a part to complete or a failure event.
                - If production completes, updates the count of produced and pending parts.
                - If a failure occurs, sets the machine state to "broken" and exits.
            - After all parts are produced, sets the machine state to "idle".
        """
        if not self.machine_state.is_state("idle"):
            self.machine_state.logs.append(
                QLogEntry(
                    timestamp=self.machine_state.get_environment().get_timestamp_now(),
                    message=f"Cannot produce parts while in state {self.machine_state.get_state()}",
                )
            )
            return

        self.machine_state.parts_pending = parts_to_produce

        self.machine_state.logs.append(
            QLogEntry(
                timestamp=self.machine_state.get_environment().get_timestamp_now(),
                message=f"Starting production of {parts_to_produce} parts.",
            )
        )

        for i in range(parts_to_produce):
            ttp = calculate_timeout_to_produce(
                self.machine_state.mean_operation_time,
                self.machine_state.sigma,
                fixed_time=self.machine_state.fixed_time,
            )
            self.machine_state.set_timeout_to_produce(ttp)
            self.event_production = self.machine_state.get_environment().timeout(ttp)

            current_task = QLogEntry(
                timestamp=self.machine_state.get_environment().get_timestamp_now(),
                duration=ttp,
                type_="Task",
                message=f"Starting production of part {i + 1}",
            )
            self.machine_state.logs.append(current_task)

            self.machine_state.set_state("working")
            self.machine_state.logs.append(
                QLogEntry(timestamp=self.machine_state.get_environment().get_timestamp_now(), message="working")
            )

            yield self.event_failure | self.event_production

            if self.event_production.processed:
                self.machine_state.update_parts_produced(+1)
                self.machine_state.update_parts_pending(-1)
                self.machine_state.logs.append(
                    QLogEntry(
                        timestamp=self.machine_state.get_environment().get_timestamp_now(), message="finished task"
                    )
                )

            elif self.event_failure.processed:

                self.machine_state.set_state("broken")
                self.machine_state.logs.append(
                    QLogEntry(
                        timestamp=self.machine_state.get_environment().get_timestamp_now(),
                        message=f"broken after {self.machine_state.get_timeout_to_failure()}",
                    )
                )

                current_task.duration = (
                    self.machine_state.get_environment().get_timestamp_now() - current_task.timestamp
                ) / 1000

                return

        self.machine_state.set_state("idle")
        self.machine_state.logs.append(
            QLogEntry(
                timestamp=self.machine_state.get_environment().get_timestamp_now(), message="idle after production"
            )
        )

        return

    def restart(self):
        """
        Restart the machine by scheduling a failure event and resuming production if there are pending parts.

        If there are parts pending, initiates the production process for the remaining parts.
        Otherwise, sets the machine state to "idle" if not already idle.
        """
        self.machine_state.set_state("idle")
        ttf = calculate_timeout_to_failure(self.machine_state.mttf, fixed_time=False)
        self.machine_state.set_timeout_to_failure(ttf)
        self.event_failure = self.machine_state.get_environment().timeout(ttf)

        if self.machine_state.parts_pending > 0:
            self.machine_state.logs.append(
                QLogEntry(
                    timestamp=self.machine_state.get_environment().get_timestamp_now(),
                    message="restarted and resuming production",
                )
            )
            self.machine_state.get_environment().process(self.produce_p(self.machine_state.parts_pending))
            return

        self.machine_state.logs.append(
            QLogEntry(timestamp=self.machine_state.get_environment().get_timestamp_now(), message="restarted and idle")
        )
