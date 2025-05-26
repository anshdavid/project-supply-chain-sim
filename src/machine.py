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
from datetime import datetime
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr
from simpy import Interrupt as simpy_interrupt, Process

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
                    start=self.get_environment().now_timestamp(),
                    content=f"Machine state changed to {state}",
                    group=self.name,
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
    def from_state(cls, env: QEnvironment, state: QMachineState):
        """
        Create a QMachine instance from the provided state.
        """

        # fmt: off
        return cls(
            env=env, name=state.name, state=state.state, mean_operation_time=state.mean_operation_time, sigma_operation_time=state.sigma_operation_time, mttf=state.mttf, fixed_time_to_produce=state.fixed_time_to_produce, fixed_time_to_failure=state.fixed_time_to_failure)  # fmt:on

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
        # self.event_failure = self.state.get_environment().timeout(0)
        # self.event_production = self.state.get_environment().timeout(0)

    def process_produce(self, parts_to_produce: int):
        """
        Simulate the production of a specified number of parts by the machine.
        """

        def recover():
            print("Recovering machine...")

        def produce():
            print("Producing parts...")

        if self.state.state != "idle":
            self.state.logs.append(
                QLogEntry.make_event(
                    start=self.state.get_environment().now_timestamp(),
                    content=f"Cannot produce parts while in state {self.state.state}",
                    group=self.state.name,
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

            start_time = self.state.get_environment().now_timestamp()
            expected_end_time = start_time + int(ttp)

            # fmt: off
            log_expected_production = QLogEntry.make_task(
                start=start_time, end=expected_end_time, content="", group=self.state.name, class_name="expected")  # fmt: on

            self.state.logs.append(log_expected_production)

            event_production = self.state.get_environment().timeout(ttp)

            yield self.event_failure | event_production

            if event_production.processed:
                self.state.parts_produced += 1
                self.state.parts_pending -= 1

                self.state.logs.append(
                    QLogEntry.make_task(
                        start=start_time,
                        end=expected_end_time,
                        content=f"Producing {i + 1} / {parts_to_produce}",
                        group=self.state.name,
                    )
                )

            elif self.event_failure.processed:
                self.state.set_state("broken")
                actual_end = self.state.get_environment().now_timestamp()
                progress = calc_task_progress(start=start_time, end=expected_end_time, actual_end=actual_end)
                self.state.logs.append(
                    QLogEntry.make_task(
                        start=start_time,
                        end=actual_end,
                        content=f"Producing {i + 1} / {parts_to_produce} failed ({progress}%)",
                        group=self.state.name,
                    )
                )
                return

        self.state.set_state("idle")
        return

    # def process_break_machine(self):
    #     """
    #     Simulate the machine breaking down when it is in the working state.
    #     If the machine is already broken, do nothing.
    #     """

    #     event_failure = self.state.get_environment().timeout(
    #         calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
    #     )

    #     while True:
    #         if self.state.state == "working" and self.event_production is not None and self.event_production.triggered:
    #             yield self.state.get_environment().timeout(1) | event_failure

    #             if event_failure.processed:
    #                 self.state.set_state("broken")
    #                 event_failure = self.state.get_environment().timeout(
    #                     calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
    #                 )
    #                 self.event_production.interrupt(f"broke after {getattr(event_failure, '_delay')} seconds working")

    #         yield self.state.get_environment().timeout(1)

    #     while True:
    #         if self.state.state == "working":
    #             ...
    #         else:
    #             self.state.get_environment().timeout(1)

    #             yield self.state.get_environment().timeout(1)

    #             repairman_ = (
    #                 yield self.state.get_factory()
    #                 .get_repairman_store()
    #                 .get(lambda repairman: repairman.state.state == "idle")
    #             )
    #             repairman = cast(QRepairman, repairman_)

    #             yield self.state.get_environment().process(repairman.process_repair_machine(self))

    #             yield self.state.get_environment().timeout(1)

    #             self.restart()

    #             self.state.get_factory().get_repairman_store().put(repairman_)
    #     if self.state.state == "broken":
    #         return

    #     self.state.set_state("broken")
    #     self.event_failure = None
    #     self.state.get_environment().timeout(0)

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
