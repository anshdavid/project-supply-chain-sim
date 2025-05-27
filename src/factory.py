from __future__ import annotations
from typing import Any, cast

from pydantic import BaseModel, Field, PrivateAttr
from simpy import Container, FilterStore, Resource

from src.environment import QEnvironment
from src.machine import QMachine
from src.repairman import QRepairman
from src.logs import QLogEntry


class QFactory:

    class QFactoryState(BaseModel):
        name: str
        meta_data: dict[str, Any] = Field(default_factory=dict, description="Metadata about the factory")

        _environment: QEnvironment = PrivateAttr()
        _machine_store: FilterStore = PrivateAttr()
        _repairman_store: FilterStore = PrivateAttr()

        logs: list[QLogEntry] = []

        def get_environment(self) -> QEnvironment:
            return self._environment

        def get_machine_store(self) -> FilterStore:
            return self._machine_store

        def get_repairman_store(self) -> FilterStore:
            return self._repairman_store

    def __init__(self, env: QEnvironment, name: str, machines: list[QMachine], repairmen: list[QRepairman]):
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
        self.state.meta_data["machines"] = machine_dict

        repairman_dict = dict()
        for repairman in repairmen:
            self.state._repairman_store.items.append(repairman)
            self._actors.append(repairman)
            repairman_dict[repairman.state.name] = {"idle": 0, "working": 0}
        self.state.meta_data["repairmen"] = repairman_dict

        self.orders = Container(env)
        self.order_semaphore = Resource(env, capacity=1)
        self.production_complete_event = env.event()

    def process_monitor_machine(self, machine: QMachine):
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
        while True:
            if machine.state.state == "idle" and self.orders.level > 0:
                yield self.orders.get(1)
                yield self.state.get_environment().process(machine.process_produce(1))
                if machine.state.parts_pending > 0:
                    self.orders.put(1)

            yield self.state.get_environment().timeout(1)

    def process_monitor_production(self):
        while True:
            if all(machine.state.state == "idle" for machine in self.state.get_machine_store().items):
                if self.orders.level == 0:
                    self.production_complete_event.succeed()
            yield self.state.get_environment().timeout(1)

    def process_monitor_states(self):
        while True:
            for actors in self._actors:
                if isinstance(actors, QMachine):
                    self.state.meta_data["machines"][actors.state.name][actors.state.state] += 0.1
                if isinstance(actors, QRepairman):
                    self.state.meta_data["repairmen"][actors.state.name][actors.state.state] += 0.1
            yield self.state.get_environment().timeout(0.1)

    def run(self, orders: int):
        for machine in self.state.get_machine_store().items:
            self.state.get_environment().process(self.process_monitor_machine(machine))
            self.state.get_environment().process(self.process_process_order(machine))

        self.orders.put(orders)

        self.state.get_environment().process(self.process_monitor_production())
        self.state.get_environment().process(self.process_monitor_states())
