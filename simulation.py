import json
from datetime import datetime, timezone

from src.factory import QFactory
from src.environment import QEnvironment
from src.logs import QSimulationLog
from src.machine import QMachine
from src.repairman import QRepairman


def test_factory(duration: int = 36000):

    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    env = QEnvironment(current_time)
    config = QFactory.QFactoryConfig(
        name="TestFactory",
        machines=[
            QMachine.QMachineConfig(
                name="M1", state="idle", mean_operation_time=1200.0, sigma=1.0, mttf=7200.0, fixed_time=True
            ),
            # QMachine.QMachineConfig(
            #     name="M2", state="idle", mean_operation_time=1200.0, sigma=1.0, mttf=7200.0, fixed_time=True
            # ),
        ],
        repairman=[QRepairman.QRepairmanConfig(name="R1", time_to_repair=300, downtime=60)],
    )
    factory = QFactory.from_config(env, config)

    factory.run()
    env.run(duration)

    sim_log = QSimulationLog.from_factory(
        launch_timestamp=env.simulation_period,
        simulation_duration=duration,
        simulation_runtime=env.now,
        description="Simulation log",
        factory=factory,
    )

    with open(r"/app/logs/simlog_log.json", "w", encoding="utf-8") as f:
        json.dump(sim_log.model_dump(), f, indent=4)


if __name__ == "__main__":
    test_factory()
