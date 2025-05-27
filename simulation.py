import json
from datetime import datetime, timezone
import random

from src.factory import QFactory
from src.environment import QEnvironment
from src.logs import QSimulationLog
from src.machine import QMachine
from src.repairman import QRepairman


def test_factory(duration: int = 36000):

    # random.seed(87)
    random.seed(17)

    current_datetime = datetime.now(timezone.utc)
    current_time = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    env = QEnvironment(current_time)
    name = "TestFactory"
    machines = [
        # fmt: off
        QMachine(
            env=env, name="M1", state="idle", mean_operation_time=600.0, sigma_operation_time=1.0, mttf=1 * 60 * 60, fixed_time_to_produce=True, fixed_time_to_failure=False, operation_cost=100.0),
        QMachine(
            env=env, name="M2", state="idle", mean_operation_time=300.0, sigma_operation_time=1.0, mttf=1 * 60 * 60, fixed_time_to_produce=True, fixed_time_to_failure=False, operation_cost=200.0),
        QMachine(
            env=env, name="M3", state="idle", mean_operation_time=60.0, sigma_operation_time=1.0, mttf=1 * 60 * 60, fixed_time_to_produce=True, fixed_time_to_failure=False, operation_cost=300.0),
        # fmt:on
    ]

    repairmen = [
        # fmt: off
        QRepairman(
            env=env, name="R1", state="idle", time_to_repair=300, sigma_time_to_repair=1.0, downtime=60, operation_cost=100.0),
        QRepairman(
            env=env, name="R2", state="idle", time_to_repair=300, sigma_time_to_repair=1.0, downtime=60, operation_cost=100.0),
        # fmt:on
    ]
    factory = QFactory(env, name=name, machines=machines, repairmen=repairmen)

    factory.run(277)
    env.run(until=factory.production_complete_event)

    # fmt: off
    sim_log = QSimulationLog.from_factory(
        launch_timestamp=env.simulation_period, simulation_duration=duration, simulation_runtime=env.now, description="Simulation log", factory=factory)  # fmt:on

    with open(r"/app/logs/viztimeline.json", "w", encoding="utf-8") as f:
        json.dump(sim_log.viz_dump(log_events=False), f, indent=4)

    with open(r"/app/logs/simulation_dump.json", "w", encoding="utf-8") as f:
        json.dump(sim_log.dump_state(factory), f, indent=4)


if __name__ == "__main__":
    test_factory()
