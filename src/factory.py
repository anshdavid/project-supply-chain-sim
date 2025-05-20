"""
factory.py
----------
Defines the QFactory class and related components for managing a simulated factory environment.

Classes:
    QFactory: Main factory class for managing machines, repairmen, and factory state.
        - QFactoryConfig: Configuration schema for initializing a factory, including machines and repairmen.
        - QFactoryLog: Represents a log entry for factory events.
        - QFactoryState: Tracks the current state, resources, and logs of the factory.

Key Features:
    - Add, remove, and manage machines and repairmen.
    - Retrieve and store resources using SimPy's FilterStore.
    - Log all significant factory events with timestamps and context.
    - Initialize factory from configuration objects.

Usage:
    Create a QFactory instance directly or via QFactory.from_config().
    Use add_machine, remove_machine, add_repairman, and remove_repairman to manage resources.
    Access logs and state via the QFactoryState inner class.
"""

from __future__ import annotations
from typing import Any, Callable, Generator, cast

from pydantic import BaseModel, Field, PrivateAttr
from simpy import FilterStore
from simpy.resources.store import FilterStoreGet

from src.environment import QEnvironment
from src.machine import QMachine
from src.repairman import QRepairman
from src.logs import QLogEntry


class QFactory:
    """
    QFactory is the main class for managing a simulated factory environment.

    Responsibilities:
        - Manages collections of machines and repairmen using SimPy's FilterStore.
        - Provides methods to add, remove, retrieve, and store machines and repairmen.
        - Maintains a log of significant factory events, including resource changes and state transitions.
        - Supports initialization from configuration objects for flexible simulation setup.
        - Integrates with a simulation environment (QEnvironment) and supports event-driven simulation.

    Inner Classes:
        QFactoryConfig: Pydantic model for factory configuration, including machine and repairman configs.
        QFactoryLog: Log entry for factory events, inheriting from LogEntry.
        QFactoryState: Tracks the current state, resources, and logs of the factory, and provides resource management methods.

    Usage:
        - Instantiate directly or via QFactory.from_config().
        - Use add_machine, remove_machine, add_repairman, and remove_repairman to manage resources.
        - Access logs and state via the QFactoryState inner class.
    """

    class QFactoryConfig(BaseModel):
        """
        Configuration schema for initializing a QFactory.
        Attributes:
            name (str): Name of the factory.
            machines (list[QMachine.QMachineConfig]): List of machine configurations.
            repairman (list[QRepairman.QRepairmanConfig]): List of repairman configurations.
        """

        name: str = Field(description="Name of the factory")
        machines: list[QMachine.QMachineConfig] = []
        repairman: list[QRepairman.QRepairmanConfig] = []

    class QFactoryLog(QLogEntry):
        """
        Represents a log entry for the factory, including timestamp, message, and optional data.
        Inherits from LogEntry.
        """

    class QFactoryState(BaseModel):
        """
        Tracks the current state, resources, and logs of the factory.

        Attributes:
            name (str): Name of the factory.
            machine_store (FilterStore): SimPy FilterStore holding QMachine instances available in the factory.
            repairman_store (FilterStore): SimPy FilterStore holding QRepairman instances available in the factory.
            logs (list[QFactory.QFactoryLog]): List of log entries for factory events.
            _environment (QEnvironment): The simulation environment associated with the factory (private).

        Methods:
            set_environment(env: QEnvironment): Set the simulation environment for the factory.
            get_environment() -> QEnvironment: Get the associated simulation environment.
            get_machine(lambda_exp: Callable[[Any], bool]) -> Generator[FilterStoreGet, None, QMachine]:
                Retrieve a machine from the store matching a filter expression.
            put_machine(machine: QMachine): Put a machine back into the store and log the event.
            get_repairman(lambda_exp: Callable[[Any], bool]) -> Generator[FilterStoreGet, None, QRepairman]:
                Retrieve a repairman from the store matching a filter expression.
            put_repairman(repairman: QRepairman): Put a repairman back into the store and log the event.
            add_log(timestamp: float, message: str, data: dict | None = None): Add a log entry to the factory's log.
        """

        name: str
        machine_store: FilterStore
        repairman_store: FilterStore

        logs: list[QFactory.QFactoryLog] = []

        _environment: QEnvironment = PrivateAttr()

        def __init__(self, name: str, env: QEnvironment):
            super().__init__(name=name)
            self._environment = env
            self.machine_store = FilterStore(env)
            self.repairman_store = FilterStore(env)

        def set_environment(self, env: QEnvironment):
            """
            Set the environment for the factory.
            Args:
                env (QEnvironment): The environment to set.
            """
            self._environment = env

        def get_environment(self) -> QEnvironment:
            """
            Get the simulation environment associated with the factory.
            Returns:
                QEnvironment: The current simulation environment.
            """
            return self._environment

        def get_machine(self, lambda_exp: Callable[[Any], bool]) -> Generator[FilterStoreGet, None, QMachine]:
            """
            Retrieve a machine from the machine store matching a filter expression.
            Args:
                lambda_exp (Callable[[Any], bool]): A filter function to select the desired machine.
            Yields:
                QMachine: The machine instance matching the filter.
            """
            machine_ = yield self.machine_store.get(lambda_exp)
            machine = cast(QMachine, machine_)

            self.add_log(
                timestamp=self._environment.now,
                message=f"Machine {machine.machine_state.name} retrieved from factory store {self.name}",
            )
            return cast(QMachine, machine)

        def put_machine(self, machine: QMachine):
            """
            Put a machine back into the machine store and log the event.
            Args:
                machine (QMachine): The machine to return to the store.
            """
            self.machine_store.put(machine)
            self.add_log(
                timestamp=self._environment.now,
                message=f"Machine {machine.machine_state.name} added to factory store {self.name}",
            )

        def get_repairman(self, lambda_exp: Callable[[Any], bool]) -> Generator[FilterStoreGet, None, QRepairman]:
            """
            Retrieve a repairman from the repairman store matching a filter expression.
            Args:
                lambda_exp (Callable[[Any], bool]): A filter function to select the desired repairman.
            Yields:
                QRepairman: The repairman instance matching the filter.
            """
            repairman_ = yield self.repairman_store.get(lambda_exp)
            repairman = cast(QRepairman, repairman_)

            self.add_log(
                timestamp=self._environment.now,
                message=f"Repairman {repairman.repairman_state.name} retrieved from factory store {self.name}",
            )
            return cast(QRepairman, repairman)

        def put_repairman(self, repairman: QRepairman):
            """
            Put a repairman back into the repairman store and log the event.
            Args:
                repairman (QRepairman): The repairman to return to the store.
            """
            self.repairman_store.put(repairman)
            self.add_log(
                timestamp=self._environment.now,
                message=f"Repairman {repairman.repairman_state.name} added to factory store {self.name}",
            )

        def add_log(self, timestamp: float, message: str, data: dict | None = None):
            """
            Add a log entry to the factory's log.
            Args:
                timestamp (float): Simulation time of the log entry.
                message (str): Log message.
                data (dict): Additional data related to the log event.
            """
            self.logs.append(QFactory.QFactoryLog(timestamp=timestamp, message=message, data=data or {}))

    @classmethod
    def from_config(cls, env: QEnvironment, config: QFactoryConfig) -> "QFactory":
        """
        Creates a QFactory instance from a configuration object.
        Args:
            env (QEnvironment): The environment in which the factory operates.
            config (QFactoryConfig): Configuration object containing factory parameters.
        Returns:
            QFactory: An instance of QFactory initialized with the provided configuration.
        """
        factory_instance = cls(name=config.name, env=env)
        for machine_config in config.machines:
            machine = QMachine.from_config(env=env, config=machine_config)
            factory_instance.add_machine(machine)
        for repair_config in config.repairman:
            repair = QRepairman.from_config(env=env, config=repair_config)
            factory_instance.add_repairman(repair)
        return factory_instance

    def __init__(self, name: str, env: QEnvironment):
        self.factory_state: QFactory.QFactoryState = QFactory.QFactoryState(name=name, env=env)
        self.factory_state._environment = env

    def add_machine(self, machine: QMachine):
        """
        Add a machine to the factory and log the operation.
        Args:
            machine (QMachine): The machine to add.
        """
        self.factory_state.machine_store.items.append(machine)
        self.factory_state.add_log(
            timestamp=self.factory_state.get_environment().now,
            message=f"Machine {machine.machine_state.name} added to factory {self.factory_state.name}",
        )

    def remove_machine(self, machine: QMachine):
        """
        Remove a machine from the factory and log the operation.
        Args:
            machine (QMachine): The machine to remove.
        """
        self.factory_state.machine_store.items.remove(machine)
        self.factory_state.add_log(
            timestamp=self.factory_state.get_environment().now,
            message=f"Machine {machine.machine_state.name} removed from factory {self.factory_state.name}",
        )

    def add_repairman(self, repairman: QRepairman):
        """
        Add a repairman to the factory and log the operation.
        Args:
            repairman (QRepairman): The repairman to add.
        """
        self.factory_state.repairman_store.items.append(repairman)
        self.factory_state.add_log(
            timestamp=self.factory_state.get_environment().now,
            message=f"Repairman {repairman.repairman_state.name} added to factory {self.factory_state.name}",
        )

    def remove_repairman(self, repairman: QRepairman):
        """
        Remove a repairman from the factory and log the operation.
        Args:
            repairman (QRepairman): The repairman to remove.
        """
        self.factory_state.repairman_store.items.remove(repairman)
        self.factory_state.add_log(
            timestamp=self.factory_state.get_environment().now,
            message=f"Repairman {repairman.repairman_state.name} removed from factory {self.factory_state.name}",
        )
