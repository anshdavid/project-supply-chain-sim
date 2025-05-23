import json
from datetime import datetime, timezone
import random

from src.factory import QFactory
from src.environment import QEnvironment
from src.logs import QSimulationLog
from src.machine import QMachine
from src.repairman import QRepairman


def test_factory(duration: int = 36000):

    random.seed(87)

    current_datetime = datetime.now(timezone.utc)
    current_time = current_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
    # file_name = current_datetime.strftime("%Y-%m-%d-%H-%M-%S")

    env = QEnvironment(current_time)
    config = QFactory.QFactoryConfig(
        name="TestFactory",
        machines=[
            QMachine.QMachineConfig(
                name="M1",
                state="idle",
                mean_operation_time=600.0,
                sigma=1.0,
                mttf=4 * 60 * 60,
                fixed_time_to_produce=True,
            ),
            QMachine.QMachineConfig(
                name="M2",
                state="idle",
                mean_operation_time=300.0,
                sigma=1.0,
                mttf=1 * 60 * 60,
                fixed_time_to_produce=True,
            ),
            QMachine.QMachineConfig(
                name="M3",
                state="idle",
                mean_operation_time=60.0,
                sigma=1.0,
                mttf=1 * 60 * 60,
                fixed_time_to_produce=True,
            ),
        ],
        repairman=[
            QRepairman.QRepairmanConfig(name="R1", time_to_repair=300, downtime=60),
            QRepairman.QRepairmanConfig(name="R2", time_to_repair=300, downtime=60),
        ],
    )
    factory = QFactory.from_config(env, config)

    factory.run(100)
    env.run(100000)

    sim_log = QSimulationLog.from_factory(
        launch_timestamp=env.simulation_period,
        simulation_duration=duration,
        simulation_runtime=env.now,
        description="Simulation log",
        factory=factory,
    )

    # with open(rf"/app/logs/{file_name}" + "_simlog.json", "w", encoding="utf-8") as f:
    #     # with open(r"/app/logs/simlog.json", "w", encoding="utf-8") as f:
    #     json.dump(sim_log.model_dump(), f, indent=4)

    # with open(rf"/app/logs/{file_name}" + "_anychart.json", "w", encoding="utf-8") as f:
    #     json.dump(sim_log.anychart_dump(), f, indent=4)

    with open(r"/app/logs/viztimeline.json", "w", encoding="utf-8") as f:
        json.dump(sim_log.viz_dump(), f, indent=4)


if __name__ == "__main__":
    test_factory()
