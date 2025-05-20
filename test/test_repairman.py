from typing import cast
import unittest
from unittest.mock import MagicMock
from src.repairman import QRepairman
from src.machine import QMachine
from src.environment import QEnvironment


class DummyEnv:
    def __init__(self):
        self.now = 0
        self.scheduled = []

    def timeout(self, delay):
        event = MagicMock()
        event.delay = delay
        self.scheduled.append(event)
        return event

    def process(self, generator):
        self.scheduled.append(generator)
        return generator


def make_repairman(name="R1", time_to_repair=10, downtime=2):
    env = DummyEnv()
    repairman = QRepairman(name=name, env=cast(QEnvironment, env), time_to_repair=time_to_repair, downtime=downtime)
    return repairman, env


def make_machine(name="M1", mean=10, sigma=2, mttf=100):
    env = DummyEnv()
    machine = QMachine(
        name=name, env=cast(QEnvironment, env), mean_operation_time=mean, sigma_operation=sigma, mttf=mttf
    )
    return machine, env


class TestQRepairman(unittest.TestCase):
    def test_initialization(self):
        repairman, _ = make_repairman()
        state = repairman.repairman_state
        self.assertEqual(state.name, "R1")
        self.assertEqual(state.time_to_repair, 10)
        self.assertEqual(state.downtime, 2)
        self.assertEqual(state.state, "idle")
        self.assertIsInstance(state.logs, list)

    def test_state_transitions(self):
        repairman, _ = make_repairman()
        state = repairman.repairman_state
        state.set_state("working")
        self.assertEqual(state.state, "working")
        state.set_state("idle")
        self.assertEqual(state.state, "idle")
        with self.assertRaises(ValueError):
            state.set_state("invalid")  # type:ignore

    def test_environment_and_factory(self):
        repairman, env = make_repairman()
        state = repairman.repairman_state
        self.assertIs(state.get_environment(), env)
        # Factory association
        dummy_factory = MagicMock()
        dummy_factory.factory_state.name = "F1"
        state.set_factory(dummy_factory)
        self.assertIs(state.get_factory(), dummy_factory)

    def test_logging(self):
        repairman, _ = make_repairman()
        state = repairman.repairman_state
        initial_log_count = len(state.logs)
        state.add_log(timestamp=1.0, message="Test log")
        self.assertTrue(len(state.logs) > initial_log_count)
        self.assertEqual(state.logs[-1].message, "Test log")

    def test_repair_machine_broken(self):
        repairman, env = make_repairman()
        machine, _ = make_machine()
        machine.machine_state.set_state("broken")
        gen = repairman.repair_machine(cast(QEnvironment, env), machine)
        # Start repair (should set states and log)
        next(gen)
        self.assertEqual(machine.machine_state.state, "repair")
        self.assertEqual(repairman.repairman_state.state, "working")
        # Complete repair (simulate timeout)
        try:
            next(gen)
        except StopIteration:
            pass
        self.assertEqual(machine.machine_state.state, "idle")
        self.assertEqual(repairman.repairman_state.state, "working")

        try:
            next(gen)
        except StopIteration:
            pass
        self.assertEqual(repairman.repairman_state.state, "idle")

        # Check logs
        messages = [log.message for log in repairman.repairman_state.logs]
        self.assertTrue(any("Repair started on machine" in m for m in messages))
        self.assertTrue(any("Repair completed on machine" in m for m in messages))

    def test_repair_machine_not_broken(self):
        repairman, env = make_repairman()
        machine, _ = make_machine()
        machine.machine_state.set_state("idle")
        gen = repairman.repair_machine(cast(QEnvironment, env), machine)
        # Should log that no repair is needed
        next(gen)
        messages = [log.message for log in repairman.repairman_state.logs]
        self.assertTrue(any("is not broken, no repair needed" in m for m in messages))
        # Should set state to idle after downtime
        try:
            next(gen)
        except StopIteration:
            pass
        self.assertEqual(repairman.repairman_state.state, "idle")


if __name__ == "__main__":
    unittest.main()
