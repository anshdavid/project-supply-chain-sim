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
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr

from src.environment import QEnvironment
from src.logs import QLogEntry
from src.utils import calc_task_progress

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
        state: Literal["idle", "working", "broken", "off"] = Field(
            description="Current operational state: idle, working, broken, off"
        )
        fixed_time_to_produce: bool = Field(
            default=True, description="Use fixed time for production and failure events"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(..., description="Standard deviation in operation time")
        fixed_time_to_failure: bool = Field(
            default=True, description="Use fixed time for production and failure events"
        )
        mttf: float = Field(description="Mean Time to Failures", gt=0)

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
        state: Literal["idle", "working", "broken", "off"] = Field(
            description="Current operational state: idle, working, broken, off"
        )
        fixed_time_to_produce: bool = Field(default=True, description="Use fixed time for production events")
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(description="Standard deviation in operation time")
        fixed_time_to_failure: bool = Field(default=False, description="Use fixed time for failure events")
        mttf: float = Field(description="Mean Time to Failures", gt=0)

        parts_produced: int = Field(default=0, description="Total parts produced by the machine")
        parts_pending: int = Field(default=0, description="Pending parts to be produced")

        logs: list[QLogEntry] = []

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)

        def set_state(self, state: Literal["idle", "working", "broken", "off"]):
            """
            Set the state of the machine.

            Args:
                state (Literal["idle", "working", "broken", "off"]): The new state to set for the machine.
            """
            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    timestamp=self.get_environment().sim_timestamp(),
                    message=f"Machine state changed to {state}",
                )
            )

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
        self.state: QMachine.QMachineState = QMachine.QMachineState(
            name=name, state="idle", mean_operation_time=mean_operation_time, sigma=sigma_operation, mttf=mttf
        )

        self.state.set_environment(env)
        self.state.set_state("idle")

        ttf = calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
        self.event_failure = self.state.get_environment().timeout(ttf)

    def process_produce(self, parts_to_produce: int):
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
        if self.state.state != "idle":
            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().sim_timestamp(),
                    message=f"Cannot produce parts while in state {self.state.state}",
                )
            )
            return

        self.state.parts_pending = parts_to_produce
        self.state.set_state("working")

        for i in range(parts_to_produce):

            ttp = calculate_timeout_to_produce(
                self.state.mean_operation_time,
                self.state.sigma,
                fixed_time=self.state.fixed_time_to_produce,
            )
            event_production = self.state.get_environment().timeout(ttp)

            # TODO: add expected task log (viz-timeline)
            current_task_log = QLogEntry.make_task(
                timestamp=self.state.get_environment().sim_timestamp(),
                duration=ttp,
                message=f"Starting production {i + 1} / {parts_to_produce}",
            )
            self.state.logs.append(current_task_log)

            yield self.event_failure | event_production

            if event_production.processed:
                self.state.parts_produced += 1
                self.state.parts_pending -= 1
                current_task_log.progress = 100
                current_task_log.data |= {"parts_produced": self.state.parts_produced}

            elif self.event_failure.processed:
                self.state.set_state("broken")

                end_time = self.state.get_environment().sim_timestamp()

                current_task_log.progress = calc_task_progress(
                    task_start_time=current_task_log.timestamp,
                    task_duration=current_task_log.duration,
                    task_actual_end_time=end_time,
                )

                # FIX: for progress bar not working
                current_task_log.duration = (end_time - current_task_log.timestamp) / 1000
                current_task_log.message += f"\n(Failed - {current_task_log.progress}%)"
                return

        self.state.set_state("idle")
        return

    def restart(self):
        """
        Restart the machine by scheduling a failure event and resuming production if there are pending parts.

        If there are parts pending, initiates the production process for the remaining parts.
        Otherwise, sets the machine state to "idle" if not already idle.
        """
        self.state.state = "idle"
        self.state.parts_pending = 0
        ttf = calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
        self.event_failure = self.state.get_environment().timeout(ttf)
