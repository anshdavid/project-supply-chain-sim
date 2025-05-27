from __future__ import annotations

import random
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr
from simpy import Interrupt as simpy_interrupt, Process

from src.environment import QEnvironment
from src.logs import QLogEntry
from src.utils import calc_task_progress

if TYPE_CHECKING:
    from src.factory import QFactory


def calculate_timeout_to_failure(mttf: float | int, fixed_time: bool = False) -> float:
    if fixed_time:
        return mttf
    else:
        return random.expovariate(1 / mttf)


def calculate_timeout_to_produce(
    mean_operation_time: float | int, sigma: float | int, fixed_time: bool = False
) -> float:
    if fixed_time:
        return mean_operation_time

    else:
        timeout_event_production = random.normalvariate(mean_operation_time, sigma)
        while timeout_event_production <= 0:
            timeout_event_production = random.normalvariate(mean_operation_time, sigma)

    return timeout_event_production


class QMachine:

    class QMachineState(BaseModel):
        name: str
        state: Literal["idle", "working", "broken", "off"] = Field(
            description="Current operational state: idle, working, broken, off"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma_operation_time: float = Field(description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        fixed_time_to_produce: bool = Field(description="Use fixed time for production events")
        fixed_time_to_failure: bool = Field(description="Use fixed time for failure events")
        operation_cost: float = Field(
            description="Cost of operating the machine per time unit working, KWpH (kilowatt per hour)", gt=0
        )

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)
        parts_produced: int = Field(default=0, description="Total parts produced by the machine")
        parts_pending: int = Field(default=0, description="Pending parts to be produced")
        logs: list[QLogEntry] = []

        def set_state(self, state: Literal["idle", "working", "broken", "off"]):
            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    start=self.get_environment().now_timestamp(),
                    content=f"Machine state changed to {state}",
                    group=self.name,
                )
            )

        def get_factory(self) -> QFactory | None:
            return self._factory

        def get_environment(self) -> QEnvironment:
            return self._environment

    # fmt: off
    def __init__(
        self, env: QEnvironment, name: str, state: Literal["idle", "working", "broken", "off"], mean_operation_time: float, sigma_operation_time: float, mttf: float, fixed_time_to_produce: bool, fixed_time_to_failure: bool, operation_cost: float
    ):  # fmt:on
        # fmt:off
        self.state: QMachine.QMachineState = QMachine.QMachineState(
            name=name, state=state, mean_operation_time=mean_operation_time, sigma_operation_time=sigma_operation_time, mttf=mttf, fixed_time_to_produce=fixed_time_to_produce, fixed_time_to_failure=fixed_time_to_failure,
            operation_cost=operation_cost)  # fmt:on

        self.state._environment = env
        ttf = calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
        self.event_failure = self.state.get_environment().timeout(ttf)
        # self.event_failure = self.state.get_environment().timeout(0)
        # self.event_production = self.state.get_environment().timeout(0)

    def process_produce(self, parts_to_produce: int):
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

    def restart(self):
        self.state.state = "idle"
        self.state.parts_pending = 0
        ttf = calculate_timeout_to_failure(self.state.mttf, fixed_time=self.state.fixed_time_to_failure)
        self.event_failure = self.state.get_environment().timeout(ttf)
