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
from socket import timeout
from typing import Any, cast

from pydantic import BaseModel, Field, PrivateAttr
from simpy import Container, FilterStore, Resource

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

        _environment: QEnvironment = PrivateAttr()
        _machine_store: FilterStore = PrivateAttr()
        _repairman_store: FilterStore = PrivateAttr()
        _meta_data: dict[str, Any] = PrivateAttr(dict())

        logs: list[QLogEntry] = []

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

        def get_repairman_store(self) -> FilterStore:
            """
            Get the repairman store.
            """

            return self._repairman_store

    @classmethod
    def from_states(
        cls,
        env: QEnvironment,
        name: str,
        machines: list[QMachine.QMachineState],
        repairmen: list[QRepairman.QRepairmanState],
    ) -> "QFactory":
        """
        Creates a QFactory instance from a configuration object.
        """

        machine_list = [QMachine.from_state(env=env, state=machine_config) for machine_config in machines]
        repairman_list = [QRepairman.from_state(env=env, state=repair_config) for repair_config in repairmen]

        factory_instance = cls(name=name, env=env, machines=machine_list, repairmen=repairman_list)

        return factory_instance

    def __init__(self, env: QEnvironment, name: str, machines: list[QMachine], repairmen: list[QRepairman]):
        """
        Initialize a QFactory instance.
        """

        self.state: QFactory.QFactoryState = QFactory.QFactoryState(name=name)
        self.state._environment = env

        self.state._machine_store = FilterStore(env)
        self.state._repairman_store = FilterStore(env)
        self._actors: list[QMachine | QRepairman] = []

        machine_dict = dict()
        for machine in machines:
            self.state._machine_store.items.append(machine)
            self._actors.append(machine)
            machine_dict[machine.state.name] = {"idle": 0, "working": 0, "broken": 0}
        self.state._meta_data["machines"] = machine_dict

        repairman_dict = dict()
        for repairman in repairmen:
            self.state._repairman_store.items.append(repairman)
            self._actors.append(repairman)
            repairman_dict[repairman.state.name] = {"idle": 0, "working": 0}
        self.state._meta_data["repairmen"] = repairman_dict

        self.orders = Container(env)
        self.order_semaphore = Resource(env, capacity=1)
        self.production_complete_event = env.event()

    def process_monitor_machine(self, machine: QMachine):
        """
        Monitor a machine's state and log significant events.
        """
        while True:
            if machine.state.state == "broken":
                self.state.get_environment().timeout(1)

                repairman_ = yield self.state.get_repairman_store().get(
                    lambda repairman: repairman.state.state == "idle"
                )
                repairman = cast(QRepairman, repairman_)

                yield self.state.get_environment().process(repairman.process_repair_machine(machine))

                yield self.state.get_environment().timeout(1)

                machine.restart()

                self.state.get_repairman_store().put(repairman_)

            yield self.state.get_environment().timeout(1)

    def process_process_order(self, machine: QMachine):
        """
        Processes orders for a given machine in a continuous loop.
        This generator function manages the production process for a machine by:
        - Checking if the machine is idle and there are pending orders.
        - Retrieving an order and initiating the production process.
        - If there are parts still pending after production, re-adding the order.
        - Yielding a timeout to simulate the passage of time in the environment.
        """

        while True:
            if machine.state.state == "idle" and self.orders.level > 0:
                yield self.orders.get(1)
                yield self.state.get_environment().process(machine.process_produce(1))
                if machine.state.parts_pending > 0:
                    self.orders.put(1)

            yield self.state.get_environment().timeout(1)

    def process_monitor_production(self):
        """
        Monitors the production process and triggers the production_complete_event when all machines are idle and there are no pending orders.

        This coroutine continuously checks if all machines in the machine store are in the "idle" state. If so, and if there are no remaining orders (orders.level == 0), it marks the production as complete by succeeding the production_complete_event. The check is performed at regular intervals defined by a timeout of 1 time unit.
        """

        while True:
            if all(machine.state.state == "idle" for machine in self.state.get_machine_store().items):
                if self.orders.level == 0:
                    self.production_complete_event.succeed()
            yield self.state.get_environment().timeout(1)

    def process_monitor_states(self):
        """
        Monitors the states of all machines and repairmen in the factory.
        """

        while True:
            for actors in self._actors:
                if isinstance(actors, QMachine):
                    self.state._meta_data["machines"][actors.state.name][actors.state.state] += 0.1
                if isinstance(actors, QRepairman):
                    self.state._meta_data["repairmen"][actors.state.name][actors.state.state] += 0.1
            yield self.state.get_environment().timeout(0.1)

    def run(self, orders: int):
        """
        Start the factory's main processes, including machine processing and monitoring.
        """

        for machine in self.state.get_machine_store().items:
            self.state.get_environment().process(self.process_monitor_machine(machine))
            self.state.get_environment().process(self.process_process_order(machine))

        self.orders.put(orders)

        self.state.get_environment().process(self.process_monitor_production())
        self.state.get_environment().process(self.process_monitor_states())
