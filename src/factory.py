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
from typing import cast

from pydantic import BaseModel, Field, PrivateAttr
from simpy import FilterStore

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
            get_all_machines() -> list[QMachine]: Return a list of all QMachine instances currently in the machine store.
        """

        name: str
        logs: list[QFactory.QFactoryLog] = []

        _environment: QEnvironment = PrivateAttr()
        _machine_store: FilterStore = PrivateAttr()
        _repairman_store: FilterStore = PrivateAttr()

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

        def get_machine_store(self) -> FilterStore:
            """
            Get the machine store.
            Returns:
                FilterStore: The machine store containing QMachine instances.
            """
            return self._machine_store

        def set_machine_store(self, machine_store: FilterStore):
            """
            Set the machine store.
            Args:
                machine_store (FilterStore): The machine store to set.
            """
            self._machine_store = machine_store

        def get_repairman_store(self) -> FilterStore:
            """
            Get the repairman store.
            Returns:
                FilterStore: The repairman store containing QRepairman instances.
            """
            return self._repairman_store

        def set_repairman_store(self, repairman_store: FilterStore):
            """
            Set the repairman store.
            Args:
                repairman_store (FilterStore): The repairman store to set.
            """
            self._repairman_store = repairman_store

        def get_all_machines(self) -> list[QMachine]:
            """
            Return a list of all QMachine instances currently in the machine store.
            Returns:
                list: List of QMachine objects in the machine store.
            """
            return self.get_machine_store().items

        def get_all_repairmen(self) -> list[QRepairman]:
            """
            Return a list of all QRepairman instances currently in the repairman store.
            Returns:
                list: List of QRepairman objects in the repairman store.
            """
            return self.get_repairman_store().items

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
            factory_instance.add_machine(machine, log=False)
        for repair_config in config.repairman:
            repair = QRepairman.from_config(env=env, config=repair_config)
            factory_instance.add_repairman(repair, log=False)
        return factory_instance

    def __init__(self, name: str, env: QEnvironment):
        self.factory_state: QFactory.QFactoryState = QFactory.QFactoryState(name=name)
        self.factory_state.set_environment(env)
        self.factory_state.set_machine_store(FilterStore(env))
        self.factory_state.set_repairman_store(FilterStore(env))

    def add_machine(self, machine: QMachine, log: bool = True):
        """
        Add a machine to the factory and log the operation.
        Args:
            machine (QMachine): The machine to add.
        """
        self.factory_state.get_machine_store().items.append(machine)
        if log:
            self.factory_state.add_log(
                timestamp=self.factory_state.get_environment().now,
                message=f"Machine {machine.machine_state.name} added to factory",
            )

    def remove_machine(self, machine: QMachine, log: bool = True):
        """
        Remove a machine from the factory and log the operation.
        Args:
            machine (QMachine): The machine to remove.
        """
        self.factory_state.get_machine_store().items.remove(machine)

    def add_repairman(self, repairman: QRepairman, log: bool = True):
        """
        Add a repairman to the factory and log the operation.
        Args:
            repairman (QRepairman): The repairman to add.
        """
        self.factory_state.get_repairman_store().items.append(repairman)
        if log:
            self.factory_state.add_log(
                timestamp=self.factory_state.get_environment().now,
                message=f"Repairman {repairman.repairman_state.name} added to factory",
            )

    def remove_repairman(self, repairman: QRepairman):
        """
        Remove a repairman from the factory and log the operation.
        Args:
            repairman (QRepairman): The repairman to remove.
        """
        self.factory_state.get_repairman_store().items.remove(repairman)
        self.factory_state.add_log(
            timestamp=self.factory_state.get_environment().now,
            message=f"Repairman {repairman.repairman_state.name} removed from factory",
        )

    def start_monitor_p(self):
        """
        Monitor the factory's processes and log significant events.
        This method can be extended to include specific monitoring logic.
        """

        def repair_p(machine: QMachine):
            """
            Repair a machine using a repairman.
            Args:
                machine (QMachine): The machine to repair.
            """
            repairman_ = yield self.factory_state.get_repairman_store().get(
                lambda repairman: repairman.repairman_state.is_state("idle")
            )
            repairman = cast(QRepairman, repairman_)
            self.factory_state.add_log(
                timestamp=self.factory_state.get_environment().now,
                message=f"Repairman {repairman.repairman_state.name} is repairing machine {machine.machine_state.name}",
            )
            yield self.factory_state.get_environment().process(repairman.repair_machine_p(machine))
            self.factory_state.add_log(
                timestamp=self.factory_state.get_environment().now,
                message=f"Repairman {repairman.repairman_state.name} finished repairing machine {machine.machine_state.name}",
            )
            self.factory_state.get_repairman_store().put(repairman)

        while True:
            for machine in self.factory_state.get_all_machines():
                if machine.machine_state.state == "broken":
                    self.factory_state.add_log(
                        timestamp=self.factory_state.get_environment().now,
                        message=f"Machine {machine.machine_state.name} is broken in factory, issuing repair",
                    )
                    self.factory_state.get_environment().process(repair_p(machine))

            yield self.factory_state.get_environment().timeout(1)

    def start_machine_p(self):
        """
        Process the machines in the factory and log the event.
        This method can be extended to include specific machine processing logic.
        """

        for machine in self.factory_state.get_all_machines():
            self.factory_state.get_environment().process(machine.produce_p(1000))
            self.factory_state.add_log(
                timestamp=self.factory_state.get_environment().now,
                message=f"Machine {machine.machine_state.name} started in factory",
            )
        yield self.factory_state.get_environment().timeout(0)

    def run(self):
        self.factory_state.get_environment().process(self.start_machine_p())
        self.factory_state.get_environment().process(self.start_monitor_p())

        # self.factory_state.get_environment().process(self.start_monitor())
        # yield self.factory_state.get_environment().timeout(0)
