"""
factory.py
----------
Defines the QFactory class and related components for managing a simulated factory environment.

Classes:
    QFactory: Main factory class for managing machines, repairmen, and factory state.
        - QFactoryConfig: Configuration schema for initializing a factory, including machines and repairmen.
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
from simpy import FilterStore, Resource

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

    class QFactoryState(BaseModel):
        """
        Tracks the current state, resources, and logs of the factory.

        Attributes:
            name (str): Name of the factory.
            machine_store (FilterStore): SimPy FilterStore holding QMachine instances available in the factory.
            repairman_store (FilterStore): SimPy FilterStore holding QRepairman instances available in the factory.
            logs (list[QLogEntry]): List of log entries for factory events.
            _environment (QEnvironment): The simulation environment associated with the factory (private).

        Methods:
            set_environment(env: QEnvironment): Set the simulation environment for the factory.
            get_environment() -> QEnvironment: Get the associated simulation environment.
            get_machine_store() -> FilterStore: Get the machine store.
            set_machine_store(machine_store: FilterStore): Set the machine store.
            get_repairman_store() -> FilterStore: Get the repairman store.
            set_repairman_store(repairman_store: FilterStore): Set the repairman store.
            get_all_machines() -> list[QMachine]: Return a list of all QMachine instances currently in the machine store.
            get_all_repairmen() -> list[QRepairman]: Return a list of all QRepairman instances currently in the repairman store.
        """

        name: str
        logs: list[QLogEntry] = []

        _environment: QEnvironment = PrivateAttr()
        _machine_store: FilterStore = PrivateAttr()
        _repairman_store: FilterStore = PrivateAttr()
        _repairman_resource: Resource = PrivateAttr()

        def set_environment(self, env: QEnvironment):
            """
            Set the environment for the factory.
            """
            self._environment = env

        def get_environment(self) -> QEnvironment:
            """
            Get the simulation environment associated with the factory.
            """
            return self._environment

        def get_machine_store(self) -> FilterStore:
            """
            Get the machine store.
            """
            return self._machine_store

        def set_machine_store(self, machine_store: FilterStore):
            """
            Set the machine store.
            """
            self._machine_store = machine_store

        def get_repairman_store(self) -> FilterStore:
            """
            Get the repairman store.
            """
            return self._repairman_store

        def set_repairman_store(self, repairman_store: FilterStore):
            """
            Set the repairman store.
            """
            self._repairman_store = repairman_store

        def set_repairman_resource(self, repairman_resource: Resource):
            """
            Set the repairman request resource.
            """
            self._repairman_resource = repairman_resource

        def get_repairman_resource(self) -> Resource:
            """
            Get the repairman request resource.
            """
            return self._repairman_resource

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

        factory_instance.state.set_repairman_resource(Resource(env, capacity=len(config.repairman)))
        return factory_instance

    def __init__(self, name: str, env: QEnvironment):
        """
        Initialize a QFactory instance.

        Args:
            name (str): Name of the factory.
            env (QEnvironment): The simulation environment associated with the factory.
        """
        self.state: QFactory.QFactoryState = QFactory.QFactoryState(name=name)
        self.state.set_environment(env)
        self.state.set_machine_store(FilterStore(env))
        self.state.set_repairman_store(FilterStore(env))

    def add_machine(self, machine: QMachine):
        """
        Add a machine to the factory and log the operation.
        """
        self.state.get_machine_store().items.append(machine)

    def add_repairman(self, repairman: QRepairman):
        """
        Add a repairman to the factory and log the operation.
        """
        self.state.get_repairman_store().items.append(repairman)

    def start_monitor_machine_p(self, machine: QMachine):
        """
        Monitor a machine's state and log significant events.
        """
        while True:
            if machine.state.state == "broken":
                self.state.logs.append(
                    QLogEntry.make_event(
                        timestamp=self.state.get_environment().sim_timestamp(),
                        message=f"Machine {machine.state.name} is broken in factory, issuing repair",
                    )
                )

                with self.state.get_repairman_resource().request() as request:
                    yield request

                    repairman_ = yield self.state.get_repairman_store().get(
                        lambda repairman: repairman.state.state == "idle"
                    )
                    repairman = cast(QRepairman, repairman_)

                    self.state.logs.append(
                        QLogEntry.make_event(
                            timestamp=self.state.get_environment().sim_timestamp(),
                            message=f"Repairman {repairman.state.name} is repairing machine {machine.state.name}",
                        )
                    )

                    yield self.state.get_environment().process(repairman.repair_machine_p(machine))

                    self.state.logs.append(
                        QLogEntry.make_event(
                            timestamp=self.state.get_environment().sim_timestamp(),
                            message=f"Repairman {repairman.state.name} finished repairing machine {machine.state.name}",
                        )
                    )

                    self.state.get_repairman_store().put(repairman_)
                    machine.restart()
                    yield self.state.get_environment().timeout(1)

            yield self.state.get_environment().timeout(1)

    def run(self, parts_to_produce: int):
        """
        Start the factory's main processes, including machine processing and monitoring.
        """

        for machine in self.state.get_machine_store().items:
            self.state.get_environment().process(machine.produce_p(parts_to_produce))
            self.state.get_environment().process(self.start_monitor_machine_p(machine))
