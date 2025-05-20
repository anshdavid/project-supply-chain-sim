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
    """

    class QRepairmanConfig(BaseModel):
        """
        Schema for configuring a repairman.
        Attributes:
            name (str): Name of the repairman.
            time_to_repair (float): Time required to repair a machine (must be > 0, <= 1000).
            downtime (float): Downtime for a repairman (must be > 0, <= 1000).
        """

        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", le=1000)

    class QRepairmanLog(QLogEntry):
        """
        Represents a log entry for the repairman, including timestamp, message, and optional data.
        Attributes:
            timestamp (float): Simulation time of the log entry.
            message (str): Log message.
            data (dict): Additional data related to the log event.
        """

    class QRepairmanState(BaseModel):
        """
        Tracks the current state and statistics of the repairman.
        Attributes:
            name (str): Name of the repairman.
            time_to_repair (float): Time required to repair a machine.
            downtime (float): Downtime for the repairman.
            state (Literal): Current state ('idle' or 'working').
            logs (list): List of QRepairmanLog entries.
        Methods:
            set_state(state): Set the repairman's state.
            get_state(): Get the current state.
            get_environment(): Get the associated environment.
            get_factory(): Get the associated factory.
            add_log(...): Add a log entry.
        """

        name: str = Field(description="Name of the repairman")
        time_to_repair: float = Field(description="Time to repair a machine", gt=0, le=1000)
        downtime: float = Field(description="Downtime for a repairman", gt=0, le=1000)
        state: Literal["idle", "working"] = Field(default="idle", description="State of the repairman")

        logs: list[QRepairman.QRepairmanLog] = []

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
            self.add_log(
                timestamp=self._environment.now,
                message=f"Repairman {self.name} state changed to {state}",
                data={"repairman": self.name, "state": state},
            )

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
            self.add_log(
                timestamp=self._environment.now,
                message=f"Repairman {self.name} associated with factory {factory.factory_state.name}",
                data={"repairman": self.name, "factory": factory.factory_state.name},
            )

        def get_factory(self) -> QFactory | None:
            """
            Get the factory associated with the repairman, if any.
            Returns:
                QFactory | None: The factory object or None.
            """
            return self._factory

        def add_log(self, timestamp: float, message: str, data: dict | None = None):
            """
            Add a log entry to the repairman's log list.
            Args:
                timestamp (float): Simulation time of the log entry.
                message (str): Log message.
                data (dict, optional): Additional data for the log entry.
            """
            log_entry = QRepairman.QRepairmanLog(timestamp=timestamp, message=message, data=data or {})
            self.logs.append(log_entry)

    @classmethod
    def from_config(cls, env: QEnvironment, config: QRepairman.QRepairmanConfig) -> QRepairman:
        """
        Creates a QRepairman instance from a configuration object.

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

    def repair_machine(self, machine: QMachine):
        """
        Simulate the repair process for a machine.
        If the machine is broken, set its state to 'repair', set the repairman to 'working',
        log the repair start, wait for the repair time, then set both to 'idle', log completion, and restart the machine.
        Args:
            env (QEnvironment): The simulation environment.
            machine (QMachine): The machine to be repaired.
        Yields:
            simpy.events.Timeout: An event representing the repair duration.
        """
        if machine.machine_state.is_state("broken"):
            machine.machine_state.set_state("repair")
            self.repairman_state.set_state("working")
            self.repairman_state.add_log(
                timestamp=self.repairman_state.get_environment().now,
                message=f"Repair started on machine {machine.machine_state.name}",
                data={"machine": machine.machine_state.name, "repairman": self.repairman_state.name},
            )
            yield self.repairman_state.get_environment().timeout(self.repairman_state.time_to_repair)
            machine.machine_state.set_state("idle")
            self.repairman_state.add_log(
                timestamp=self.repairman_state.get_environment().now,
                message=f"Repair completed on machine {machine.machine_state.name}",
                data={"machine": machine.machine_state.name, "repairman": self.repairman_state.name},
            )
            machine.restart()
        else:
            self.repairman_state.add_log(
                timestamp=self.repairman_state.get_environment().now,
                message=f"Machine {machine.machine_state.name} is not broken, no repair needed",
                data={"machine": machine.machine_state.name, "repairman": self.repairman_state.name},
            )
        yield self.repairman_state.get_environment().timeout(self.repairman_state.downtime)
        if not self.repairman_state.is_state("idle"):
            self.repairman_state.set_state("idle")
