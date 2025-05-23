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
import sys
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

    Methods:
        from_config(env, config): Instantiate a QRepairman from a configuration object.
        repair_machine_p(machine): Simulate the repair process for a machine.
    """

    class QRepairmanConfig(BaseModel):
        """
        Configuration schema for a QRepairman.

        Attributes:
            name (str): Name of the repairman.
            time_to_repair (float): Time required to repair a machine (must be > 0, <= 1000).
            downtime (float): Downtime for a repairman (must be > 0, <= 1000).
        """

        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", le=1000)

    class QRepairmanState(BaseModel):
        """
        Tracks the current state, statistics, and logs of the repairman.

        Attributes:
            name (str): Name of the repairman.
            time_to_repair (float): Time required to repair a machine.
            downtime (float): Downtime for the repairman.
            state (Literal): Current state ('idle' or 'working').
            logs (list[QLogEntry]): List of log entries for the repairman.
        """

        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", gt=0, le=1000)
        state: Literal["idle", "working"] = Field(default="idle", description="State of the repairman")

        logs: list[QLogEntry] = []

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)

        def set_state(self, state: Literal["idle", "working"]):
            """
            Set the state of the repairman.
            Args:
                state (Literal["idle", "working"]): The new state to set.
            Raises:
                ValueError: If the state is not valid.
            """

            self.state = state
            self.logs.append(
                QLogEntry.make_event(
                    timestamp=self._environment.sim_timestamp(),
                    message=f"Repairman {self.name} state changed to {state}",
                )
            )

        def set_environment(self, env: QEnvironment):
            """
            Set the environment associated with the repairman.
            Args:
                env (QEnvironment): The environment object to associate.
            """
            self._environment = env

        def get_environment(self) -> QEnvironment:
            """
            Get the environment associated with the repairman.
            Returns:
                QEnvironment: The environment object.
            """
            return self._environment

        def set_factory(self, factory: QFactory):
            """
            Set the factory associated with the repairman.
            Args:
                factory (QFactory): The factory object to associate.
            """
            self._factory = factory

        def get_factory(self) -> QFactory | None:
            """
            Get the factory associated with the repairman, if any.
            Returns:
                QFactory | None: The factory object or None.
            """
            return self._factory

    @classmethod
    def from_config(cls, env: QEnvironment, config: QRepairman.QRepairmanConfig) -> QRepairman:
        """
        Create a QRepairman instance from a configuration object.

        Args:
            env (QEnvironment): The environment in which the repairman operates.
            config (QRepairman.QRepairmanConfig): Configuration object containing repairman parameters.

        Returns:
            QRepairman: An instance of QRepairman initialized with the provided configuration.
        """
        return cls(
            name=config.name,
            env=env,
            time_to_repair=config.time_to_repair,
            downtime=config.downtime,
        )

    def __init__(self, name: str, env: QEnvironment, time_to_repair: float = 30, downtime: float = 1.5):
        """
        Initialize a QRepairman instance with the given parameters.
        Args:
            name (str): Name of the repairman.
            time_to_repair (float): Time required to repair a machine.
            downtime (float): Downtime for the repairman.
        """
        self.state: QRepairman.QRepairmanState = QRepairman.QRepairmanState(
            name=name,
            time_to_repair=time_to_repair,
            downtime=downtime,
        )

        self.state.set_environment(env)

    def process_repair_machine(self, machine: QMachine):
        """
        Simulate the repair process for a machine.
        If the machine is broken, set its state to 'repair', set the repairman to 'working',
        log the repair start, wait for the repair time, then set both to 'idle', log completion, and restart the machine.
        Args:
            machine (QMachine): The machine to be repaired.
        Yields:
            simpy.events.Timeout: An event representing the repair duration and downtime.
        """
        if not self.state.state == "idle":
            self.state.logs.append(
                QLogEntry(
                    timestamp=self.state.get_environment().sim_timestamp(),
                    message=f"Repairman {self.state.name} is busy, cannot repair machine {machine.state.name}",
                )
            )
            return

        if machine.state.state == "broken":
            self.state.state = "working"
            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().sim_timestamp(),
                    message=f"Repairman started work on machine {machine.state.name}",
                )
            )

            repair_task_log = QLogEntry.make_task(
                timestamp=self.state.get_environment().sim_timestamp(),
                duration=self.state.time_to_repair,
                message=f"Repair {machine.state.name}",
            )
            self.state.logs.append(repair_task_log)

            yield self.state.get_environment().timeout(self.state.time_to_repair)
            repair_task_log.progress = 100

            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().sim_timestamp(),
                    message=f"Repair completed work on machine {machine.state.name}",
                )
            )
            self.state.state = "idle"
        else:
            self.state.logs.append(
                QLogEntry.make_event(
                    timestamp=self.state.get_environment().sim_timestamp(),
                    message=f"Machine {machine.state.name} is not broken, no repair needed",
                )
            )
