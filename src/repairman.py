"""
repairman.py
------------
Defines the QRepairman class for modeling repairman agents in a factory simulation.

Features:
    - QRepairman: Simulates a repairman responsible for repairing machines.
    - QRepairmanConfig: Configuration schema for initializing a repairman.
    - QRepairmanState: Tracks the current state, statistics, and logs of the repairman.
    - Methods for state management, environment/factory association, and repair process simulation.

Usage:
    - Use QRepairman.from_config() or QRepairman.__init__() to create a repairman.
    - Use repair_machine_p() to simulate the repair process for a machine.

Dependencies:
    - pydantic: For configuration and state models.
    - src.environment.QEnvironment: The simulation environment.
    - src.factory.QFactory: The factory context (referenced via TYPE_CHECKING).
    - src.machine.QMachine: The machine to be repaired (referenced via TYPE_CHECKING).
    - src.logs.QLogEntry: Base class for log entries.
"""

from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr

from src.environment import QEnvironment
from src.logs import QLogEntry

if TYPE_CHECKING:
    from src.factory import QFactory
    from src.machine import QMachine


class QRepairman:
    """
    QRepairman models a repairman entity responsible for repairing machines in the simulation.
    Contains configuration, state, and logging for repairman activities.

    Responsibilities:
        - Tracks repairman state, repair and downtime durations, and logs.
        - Integrates with QFactory and QEnvironment.
        - Simulates the repair process for machines.

    Inner Classes:
        QRepairmanConfig: Configuration schema for initializing a repairman.
        QRepairmanState: Tracks the current state, statistics, and logs of the repairman.
    """

    class QRepairmanConfig(BaseModel):
        """
        Configuration schema for a QRepairman.
        """

        name: str = Field(description="Name of the repairman")
        state: Literal["idle", "working"] = Field(description="State of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0)
        sigma_time_to_repair: float = Field(description="Standard deviation of repair time", gt=0)
        downtime: float = Field(description="Downtime for a repairman")

    class QRepairmanState(BaseModel):
        """
        Tracks the current state, statistics, and logs of the repairman.
        """

        name: str = Field(description="Name of the repairman")
        state: Literal["idle", "working"] = Field(description="State of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0)
        sigma_time_to_repair: float = Field(description="Standard deviation of repair time", gt=0)
        downtime: float = Field(description="Downtime for a repairman")

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory = PrivateAttr()
        logs: list[QLogEntry] = []

        def set_state(self, state: Literal["idle", "working"]):
            """
            Set the state of the repairman.
            """

            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    timestamp=self._environment.now_timestamp(),
                    message=f"Repairman {self.name} state changed to {state}",
                )
            )

        def get_environment(self) -> QEnvironment:
            """
            Get the environment associated with the repairman.
            """

            return self._environment

        def get_factory(self) -> QFactory | None:
            """
            Get the factory associated with the repairman, if any.
            """

            return self._factory

    @classmethod
    def from_config(cls, env: QEnvironment, config: QRepairman.QRepairmanConfig) -> QRepairman:
        """
        Create a QRepairman instance from a configuration object.
        """

        # fmt: off
        return cls(
            env=env, name=config.name, state=config.state, time_to_repair=config.time_to_repair, sigma_time_to_repair=config.sigma_time_to_repair, downtime=config.downtime)  # fmt:on

    # fmt: off
    def __init__(
            self, env: QEnvironment, name: str, state: Literal["idle", "working"], time_to_repair: float, sigma_time_to_repair: float, downtime: float):  # fmt:on
        """
        Initialize a QRepairman instance with the given parameters.
        """

        # fmt:off
        self.state: QRepairman.QRepairmanState = QRepairman.QRepairmanState(
            name=name, state=state, time_to_repair=time_to_repair, sigma_time_to_repair=sigma_time_to_repair, downtime=downtime)  # fmt:on

        self.state._environment = env

    def process_repair_machine(self, machine: QMachine):
        """
        Simulate the repair process for a machine.
        If the machine is broken, set its state to 'repair', set the repairman to 'working',
        log the repair start, wait for the repair time, then set both to 'idle', log completion, and restart the machine.
        """
        if not self.state.state == "idle":
            self.state.logs.append(
                QLogEntry(
                    timestamp=self.state.get_environment().now_timestamp(),
                    message=f"Repairman {self.state.name} is busy, cannot repair machine {machine.state.name}",
                )
            )
            return

        if machine.state.state == "broken":
            self.state.set_state("working")

            repair_task_log = QLogEntry.make_task(
                timestamp=self.state.get_environment().now_timestamp(),
                duration=self.state.time_to_repair,
                message=f"Repair {machine.state.name}",
            )
            self.state.logs.append(repair_task_log)

            yield self.state.get_environment().timeout(self.state.time_to_repair)
            repair_task_log.progress = 100
            self.state.set_state("idle")

        else:
            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().now_timestamp(),
                    message=f"Machine {machine.state.name} is not broken, no repair needed",
                )
            )
