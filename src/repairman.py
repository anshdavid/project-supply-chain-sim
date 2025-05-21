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
            if state not in ["idle", "working"]:
                raise ValueError("Invalid state")
            self.state = state

        def get_state(self) -> Literal["idle", "working"]:
            """
            Get the current state of the repairman.
            Returns:
                Literal["idle", "working"]: The current state.
            """
            return self.state

        def is_state(self, state: Literal["idle", "working"]) -> bool:
            """
            Check if the repairman is in a specific state.
            Args:
                state (Literal["idle", "working"]): The state to check.
            Returns:
                bool: True if the repairman is in the specified state, False otherwise.
            """
            return self.state == state

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
        self.repairman_state: QRepairman.QRepairmanState = QRepairman.QRepairmanState(
            name=name,
            time_to_repair=time_to_repair,
            downtime=downtime,
        )

        self.repairman_state.set_environment(env)

    def repair_machine_p(self, machine: QMachine):
        """
        Simulate the repair process for a machine.
        If the machine is broken, set its state to 'repair', set the repairman to 'working',
        log the repair start, wait for the repair time, then set both to 'idle', log completion, and restart the machine.
        Args:
            machine (QMachine): The machine to be repaired.
        Yields:
            simpy.events.Timeout: An event representing the repair duration and downtime.
        """
        if machine.machine_state.is_state("broken"):
            machine.machine_state.set_state("repair")
            self.repairman_state.set_state("working")
            self.repairman_state.logs.append(
                QLogEntry(
                    timestamp=self.repairman_state.get_environment().now,
                    message=f"Repairman started work on machine {machine.machine_state.name}",
                )
            )
            yield self.repairman_state.get_environment().timeout(self.repairman_state.time_to_repair)
            self.repairman_state.logs.append(
                QLogEntry(
                    timestamp=self.repairman_state.get_environment().now,
                    message=f"Repair completed work on machine {machine.machine_state.name}",
                )
            )
            machine.restart()
        else:
            self.repairman_state.logs.append(
                QLogEntry(
                    timestamp=self.repairman_state.get_environment().now,
                    message=f"Machine {machine.machine_state.name} is not broken, no repair needed",
                )
            )
        yield self.repairman_state.get_environment().timeout(self.repairman_state.downtime)

        if not self.repairman_state.is_state("idle"):
            self.repairman_state.set_state("idle")
            self.repairman_state.logs.append(
                QLogEntry(
                    timestamp=self.repairman_state.get_environment().now,
                    message="Repairman is now idle",
                )
            )
