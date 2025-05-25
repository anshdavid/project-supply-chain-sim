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

    env = QEnvironment(current_time)
    config = QFactory.QFactoryConfig(
        name="TestFactory",
        machines=[
            QMachine.QMachineConfig(
                name="M1",
                state="idle",
                mean_operation_time=600.0,
                sigma_operation_time=1.0,
                mttf=1 * 60 * 60,
                fixed_time_to_produce=True,
                fixed_time_to_failure=False,
            ),
            QMachine.QMachineConfig(
                name="M2",
                state="idle",
                mean_operation_time=300.0,
                sigma_operation_time=1.0,
                mttf=1 * 60 * 60,
                fixed_time_to_produce=True,
                fixed_time_to_failure=False,
            ),
            QMachine.QMachineConfig(
                name="M3",
                state="idle",
                mean_operation_time=60.0,
                sigma_operation_time=1.0,
                mttf=1 * 60 * 60,
                fixed_time_to_produce=True,
                fixed_time_to_failure=False,
            ),
        ],
        repairman=[
            QRepairman.QRepairmanConfig(
                name="R1", state="idle", time_to_repair=300, sigma_time_to_repair=1.0, downtime=60
            ),
            QRepairman.QRepairmanConfig(
                name="R2", state="idle", time_to_repair=300, sigma_time_to_repair=1.0, downtime=60
            ),
        ],
    )
    factory = QFactory.from_config(env, config)

    factory.run(277)
    env.run(until=factory.production_complete_event)

    # fmt: off
    sim_log = QSimulationLog.from_factory(
        launch_timestamp=env.simulation_period, simulation_duration=duration, simulation_runtime=env.now, description="Simulation log", factory=factory)  # fmt:on

    # print(env.now)
    # for machine in factory.state.get_machine_store().items:
    #     print(machine.state.parts_produced)

    # with open(rf"/app/logs/{file_name}" + "_simlog.json", "w", encoding="utf-8") as f:
    #     # with open(r"/app/logs/simlog.json", "w", encoding="utf-8") as f:
    #     json.dump(sim_log.model_dump(), f, indent=4)

    # with open(rf"/app/logs/{file_name}" + "_anychart.json", "w", encoding="utf-8") as f:
    #     json.dump(sim_log.anychart_dump(), f, indent=4)

    with open(r"/app/logs/viztimeline.json", "w", encoding="utf-8") as f:
        json.dump(sim_log.viz_dump(log_events=False), f, indent=4)


if __name__ == "__main__":
    test_factory()
