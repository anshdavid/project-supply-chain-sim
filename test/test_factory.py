import pprint
import unittest

from numpy import True_
from src.environment import QEnvironment
from src.factory import QFactory
from src.machine import QMachine
from src.repairman import QRepairman


class TestQFactory(unittest.TestCase):
    def setUp(self):
        self.env = QEnvironment()
        self.config = QFactory.QFactoryConfig(
            name="TestFactory",
            machines=[QMachine.QMachineConfig(name="M1", state="idle", mean_operation_time=5.0, sigma=1.0, mttf=100.0)],
            repairman=[QRepairman.QRepairmanConfig(name="R1", time_to_repair=1, downtime=1)],
        )
        self.factory = QFactory.from_config(self.env, self.config)

    def test_factory_initialization(self):
        self.assertEqual(self.factory.factory_state.name, self.config.name)
        self.assertEqual(len(self.factory.factory_state._machine_store.items), len(self.config.machines))
        self.assertEqual(len(self.factory.factory_state._repairman_store.items), len(self.config.repairman))

    def test_add_and_remove_machine(self):
        machine = QMachine.from_config(
            self.env, QMachine.QMachineConfig(name="M2", state="idle", mean_operation_time=4.0, sigma=0.5, mttf=80.0)
        )
        self.factory.add_machine(machine)
        self.assertIn(machine, self.factory.factory_state._machine_store.items)
        self.factory.remove_machine(machine)
        self.assertNotIn(machine, self.factory.factory_state._machine_store.items)

    def test_add_and_remove_repairman(self):
        repairman = QRepairman.from_config(
            self.env, QRepairman.QRepairmanConfig(name="R2", time_to_repair=1, downtime=1)
        )
        self.factory.add_repairman(repairman)
        self.assertIn(repairman, self.factory.factory_state._repairman_store.items)
        self.factory.remove_repairman(repairman)
        self.assertNotIn(repairman, self.factory.factory_state._repairman_store.items)

    def test_factory_logging_on_machine_add_remove(self):
        machine = QMachine.from_config(
            self.env, QMachine.QMachineConfig(name="M3", state="idle", mean_operation_time=3.0, sigma=0.2, mttf=60.0)
        )
        initial_log_count = len(self.factory.factory_state.logs)
        self.factory.add_machine(machine)
        self.assertTrue(
            any(
                f"Machine {machine.machine_state.name} added" in log.message
                for log in self.factory.factory_state.logs[initial_log_count:]
            )
        )
        self.factory.remove_machine(machine)
        self.assertTrue(
            any(
                f"Machine {machine.machine_state.name} removed" in log.message
                for log in self.factory.factory_state.logs[initial_log_count:]
            )
        )

    def test_factory_logging_on_repairman_add_remove(self):
        repairman = QRepairman.from_config(
            self.env, QRepairman.QRepairmanConfig(name="R3", time_to_repair=1, downtime=1)
        )
        initial_log_count = len(self.factory.factory_state.logs)
        self.factory.add_repairman(repairman)
        self.assertTrue(
            any(
                f"Repairman {repairman.repairman_state.name} added" in log.message
                for log in self.factory.factory_state.logs[initial_log_count:]
            )
        )
        self.factory.remove_repairman(repairman)
        self.assertTrue(
            any(
                f"Repairman {repairman.repairman_state.name} removed" in log.message
                for log in self.factory.factory_state.logs[initial_log_count:]
            )
        )

    def test_factory_state_environment(self):
        self.assertIs(self.factory.factory_state.get_environment(), self.env)
        new_env = QEnvironment()
        self.factory.factory_state.set_environment(new_env)
        self.assertIs(self.factory.factory_state.get_environment(), new_env)

    def test_factory_machine_store_get_put(self):
        machine = QMachine.from_config(
            self.env, QMachine.QMachineConfig(name="M4", state="idle", mean_operation_time=2.0, sigma=0.1, mttf=50.0)
        )
        self.factory.add_machine(machine)

        def filter_fn(m: QMachine):
            return m.machine_state.name == "M4"

        gen = self.factory.factory_state.get_machine(filter_fn)
        self.env.process(gen)
        self.env.run(until=4)

        pprint.pprint(self.factory.factory_state.logs)
        self.assertTrue(any(log.message.startswith("Machine M4 retrieved") for log in self.factory.factory_state.logs))

    def test_factory_repairman_store_get_put(self):
        repairman = QRepairman.from_config(
            self.env, QRepairman.QRepairmanConfig(name="R4", time_to_repair=1, downtime=1)
        )
        self.factory.add_repairman(repairman)
        self.factory.factory_state.put_repairman(repairman)

        def filter_fn(r):
            return r.repairman_state.name == "R4"

        gen = self.factory.factory_state.get_repairman(filter_fn)
        self.env.process(gen)
        self.env.run(until=4)
        self.assertTrue(
            any(log.message.startswith("Repairman R4 retrieved") for log in self.factory.factory_state.logs)
        )

    def test_factory_log_entry(self):
        self.factory.factory_state.add_log(0.0, "Test log entry", {"foo": "bar"})
        self.assertTrue(
            any(log.message == "Test log entry" and log.data["foo"] == "bar" for log in self.factory.factory_state.logs)
        )


if __name__ == "__main__":
    unittest.main()
