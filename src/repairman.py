from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr

from src.environment import QEnvironment
from src.logs import QLogEntry

if TYPE_CHECKING:
    from src.factory import QFactory
    from src.machine import QMachine


class QRepairman:

    class QRepairmanState(BaseModel):
        name: str = Field(description="Name of the repairman")
        state: Literal["idle", "working"] = Field(description="State of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0)
        sigma_time_to_repair: float = Field(description="Standard deviation of repair time", gt=0)
        downtime: float = Field(description="Downtime for a repairman")
        operation_cost: float = Field(description="Operation cost of the repairman, dollar per hour", gt=0)

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory = PrivateAttr()
        logs: list[QLogEntry] = []

        def set_state(self, state: Literal["idle", "working"]):
            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    start=self._environment.now_timestamp(),
                    content=f"Repairman {self.name} state changed to {state}",
                    group=self.name,
                )
            )

        def get_environment(self) -> QEnvironment:
            return self._environment

        def get_factory(self) -> QFactory | None:

            return self._factory

    # fmt: off
    def __init__(
            self, env: QEnvironment, name: str, state: Literal["idle", "working"], time_to_repair: float, sigma_time_to_repair: float, downtime: float, operation_cost: float):  # fmt:on
        # fmt:off
        self.state: QRepairman.QRepairmanState = QRepairman.QRepairmanState(
            name=name, state=state, time_to_repair=time_to_repair, sigma_time_to_repair=sigma_time_to_repair, downtime=downtime, operation_cost=operation_cost)  # fmt:on

        self.state._environment = env

    def process_repair_machine(self, machine: QMachine):
        if not self.state.state == "idle":
            self.state.logs.append(
                QLogEntry.make_event(
                    start=self.state.get_environment().now_timestamp(),
                    content=f"Repairman {self.state.name} is busy, cannot repair machine {machine.state.name}",
                    group=self.state.name,
                )
            )
            return

        if machine.state.state == "broken":
            self.state.set_state("working")

            repair_task_log = QLogEntry.make_task(
                start=self.state.get_environment().now_timestamp(),
                end=self.state.get_environment().now_timestamp(self.state.time_to_repair),
                content=f"Repair {machine.state.name}",
                group=self.state.name,
            )
            self.state.logs.append(repair_task_log)

            yield self.state.get_environment().timeout(self.state.time_to_repair)
            self.state.set_state("idle")

        else:
            self.state.logs.append(
                QLogEntry.make_event(
                    start=self.state.get_environment().now_timestamp(),
                    content=f"Machine {machine.state.name} is not broken, no repair needed",
                    group=self.state.name,
                )
            )
