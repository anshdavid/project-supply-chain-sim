import pprint
from src.factory import QFactory
from src.environment import QEnvironment
from src.machine import QMachine
from src.repairman import QRepairman


def test_factory():
    env = QEnvironment()
    config = QFactory.QFactoryConfig(
        name="TestFactory",
        machines=[QMachine.QMachineConfig(name="M1", state="idle", mean_operation_time=5.0, sigma=1.0, mttf=500.0)],
        repairman=[QRepairman.QRepairmanConfig(name="R1", time_to_repair=5, downtime=1)],
    )
    factory = QFactory.from_config(env, config)

    factory.run()
    env.run(10000)

    for machine in factory.factory_state.get_all_machines():
        print(machine.machine_state.parts_produced, machine.machine_state.parts_pending)

    # for machine in factory.factory_state.get_all_machines():
    #     pprint.pprint(machine.machine_state.logs[-10:])

    # for repairman in factory.factory_state.get_all_repairmen():
    #     pprint.pprint(repairman.repairman_state.logs[-10:])


if __name__ == "__main__":
    test_factory()
