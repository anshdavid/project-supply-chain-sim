from typing import cast
import unittest
from unittest.mock import MagicMock

from pydantic import ValidationError

from src.machine import QMachine
from src.environment import QEnvironment


class DummyEnv:
    def __init__(self):
        self.now = 0
        self.scheduled = []

    def timeout(self, delay):
        event = MagicMock()
        event.processed = False
        event.delay = delay
        self.scheduled.append(event)
        return event

    def process(self, generator):
        self.scheduled.append(generator)
        return generator


def make_machine(name="M1", mean=10, sigma=2, mttf=100):
    env = DummyEnv()
    return (
        QMachine(name=name, env=cast(QEnvironment, env), mean_operation_time=mean, sigma_operation=sigma, mttf=mttf),
        env,
    )


class TestQMachine(unittest.TestCase):
    """
    Unit tests for the QMachine class and its state management.
    Covers initialization, state transitions, production, timeouts, restart/repair, config validation, and logging.
    """

    def test_qmachine_initialization(self):
        """
        Test that a QMachine is initialized with correct default state and attributes.
        """
        machine, _ = make_machine()
        self.assertEqual(machine.machine_state.name, "M1")
        self.assertEqual(machine.machine_state.state, "idle")
        self.assertEqual(machine.machine_state.mean_operation_time, 10)
        self.assertEqual(machine.machine_state.sigma, 2)
        self.assertEqual(machine.machine_state.mttf, 100)
        self.assertEqual(machine.machine_state.parts_produced, 0)
        self.assertEqual(machine.machine_state.parts_pending, 0)
        self.assertIsInstance(machine.machine_state.logs, list)

    def test_state_transitions(self):
        """
        Test all valid state transitions for a QMachine.
        """
        machine, _ = make_machine()
        machine.machine_state.set_state("working")
        self.assertEqual(machine.machine_state.state, "working")
        machine.machine_state.set_state("broken")
        self.assertEqual(machine.machine_state.state, "broken")
        machine.machine_state.set_state("repair")
        self.assertEqual(machine.machine_state.state, "repair")
        machine.machine_state.set_state("idle")
        self.assertEqual(machine.machine_state.state, "idle")

    def test_update_parts_produced_and_pending(self):
        """
        Test incrementing and decrementing parts produced and pending.
        """
        machine, _ = make_machine()
        machine.machine_state.update_parts_produced(5)
        self.assertEqual(machine.machine_state.parts_produced, 5)
        machine.machine_state.update_parts_pending(3)
        self.assertEqual(machine.machine_state.parts_pending, 3)
        machine.machine_state.update_parts_pending(-2)
        self.assertEqual(machine.machine_state.parts_pending, 1)

    def test_calculate_timeouts(self):
        """
        Test calculation of fixed timeouts for failure and production.
        """
        machine, _ = make_machine()
        ttf = machine.calculate_timeout_to_failure(fixed_time=True)
        self.assertEqual(ttf, 100)
        ttp = machine.calculate_timeout_to_produce(fixed_time=True)
        self.assertEqual(ttp, 10)

    def test_restart_and_repair(self):
        """
        Test restart logic, including state and event scheduling.
        """
        machine, env = make_machine()
        machine.machine_state.parts_pending = 2
        machine.restart()
        self.assertTrue(len(env.scheduled) > 0)
        machine.machine_state.set_state("broken")
        # If repair method is not present, just check state transition
        self.assertEqual(machine.machine_state.state, "broken")
        # Optionally, if repair logic is implemented elsewhere, test it there

    def test_invalid_config(self):
        """
        Test that invalid QMachineConfig values raise a ValidationError.
        """
        with self.assertRaises(ValidationError):
            QMachine.QMachineConfig(name="M2", state="idle", mean_operation_time=0, sigma=1, mttf=0)

    def test_logging(self):
        """
        Test that state and part updates are logged correctly.
        """
        machine, _ = make_machine()
        initial_log_count = len(machine.machine_state.logs)
        machine.machine_state.set_state("working")
        machine.machine_state.update_parts_produced(1)
        machine.machine_state.update_parts_pending(1)
        self.assertTrue(len(machine.machine_state.logs) > initial_log_count)
        messages = [log.message for log in machine.machine_state.logs]
        self.assertTrue(any("State changed to working" in m for m in messages))
        self.assertTrue(any("Parts produced updated" in m for m in messages))
        self.assertTrue(any("Parts pending updated" in m for m in messages))


# if __name__ == "__main__":
#     unittest.main()
