"""
machine.py
----------
Provides the QMachine class and supporting utilities for simulating a production machine in a factory environment.

Classes:
    QMachine: Simulates a production machine, tracking operational state, production statistics, and logs.
        - QMachineConfig: Configuration schema for initializing a QMachine.
        - QMachineState: Tracks the current state and statistics of the machine, and provides methods for state and production updates.

Functions:
    calculate_timeout_to_failure: Calculate the time to the next failure event based on MTTF.
    calculate_timeout_to_produce: Calculate the time required to produce a part based on mean and sigma.

Usage:
    - Use QMachine.from_config() or QMachine.__init__() to create a machine.
    - Use process_produce() to start production of parts.
    - Use restart() to resume operation after repair or failure.
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
    """

    class QMachineConfig(BaseModel):
        """
        Configuration schema for a QMachine.
        """

        name: str = Field(description="Name of the machine")
        state: Literal["idle", "working", "broken", "off"] = Field(
            description="Current operational state: idle, working, broken, off"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma_operation_time: float = Field(description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        fixed_time_to_produce: bool = Field(description="Use fixed time for production events")
        fixed_time_to_failure: bool = Field(description="Use fixed time for failure events")

    class QMachineState(BaseModel):
        """
        Represents the operational state and statistics of a machine.
        """

        name: str
        state: Literal["idle", "working", "broken", "off"] = Field(
            description="Current operational state: idle, working, broken, off"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma_operation_time: float = Field(description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        fixed_time_to_produce: bool = Field(description="Use fixed time for production events")
        fixed_time_to_failure: bool = Field(description="Use fixed time for failure events")

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)
        parts_produced: int = Field(default=0, description="Total parts produced by the machine")
        parts_pending: int = Field(default=0, description="Pending parts to be produced")
        logs: list[QLogEntry] = []

        def set_state(self, state: Literal["idle", "working", "broken", "off"]):
            """
            Set the state of the machine and log the state change.
            """

            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    timestamp=self.get_environment().now_timestamp(), message=f"Machine state changed to {state}"
                )
            )

        def get_factory(self) -> QFactory | None:
            """
            Get the associated QFactory instance if available.
            """

            return self._factory

        def get_environment(self) -> QEnvironment:
            """
            Get the current QEnvironment instance associated with the machine.
            """

            return self._environment

    @classmethod
    def from_config(cls, env: QEnvironment, config: QMachineConfig):
        """
        Create a QMachine instance from the provided configuration.
        """

        # fmt: off
        return cls(
            env=env, name=config.name, state=config.state, mean_operation_time=config.mean_operation_time, sigma_operation_time=config.sigma_operation_time, mttf=config.mttf, fixed_time_to_produce=config.fixed_time_to_produce, fixed_time_to_failure=config.fixed_time_to_failure)  # fmt:on

    # fmt: off
    def __init__(
        self, env: QEnvironment, name: str, state: Literal["idle", "working", "broken", "off"], mean_operation_time: float, sigma_operation_time: float, mttf: float, fixed_time_to_produce: bool, fixed_time_to_failure: bool
    ):  # fmt:on
        """
        Initialize a QMachine with the given parameters and set up its state and event timers.
        """

        # fmt:off
        self.state: QMachine.QMachineState = QMachine.QMachineState(
            name=name, state=state, mean_operation_time=mean_operation_time, sigma_operation_time=sigma_operation_time, mttf=mttf, fixed_time_to_produce=fixed_time_to_produce, fixed_time_to_failure=fixed_time_to_failure
        )  # fmt:on

        self.state._environment = env
        ttf = calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
        self.event_failure = self.state.get_environment().timeout(ttf)

    def process_produce(self, parts_to_produce: int):
        """
        Simulate the production of a specified number of parts by the machine.
        """

        if self.state.state != "idle":
            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().now_timestamp(),
                    message=f"Cannot produce parts while in state {self.state.state}",
                )
            )
            return

        self.state.parts_pending = parts_to_produce
        self.state.set_state("working")

        for i in range(parts_to_produce):

            ttp = calculate_timeout_to_produce(
                self.state.mean_operation_time,
                self.state.sigma_operation_time,
                fixed_time=self.state.fixed_time_to_produce,
            )
            event_production = self.state.get_environment().timeout(ttp)

            # TODO: add expected task log (viz-timeline)
            current_task_log = QLogEntry.make_task(
                timestamp=self.state.get_environment().now_timestamp(),
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

                end_time = self.state.get_environment().now_timestamp()

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
