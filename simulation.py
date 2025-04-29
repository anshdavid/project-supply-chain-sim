import json
import random
from src.manufacturer import Factory
from src.environment import Environment
from src.schema import EnhancedJSONEncoder


def test_machine():
    """
    test_machine _summary_

    _extended_summary_
    """

    random.seed(120)

    print("=== machine: 3, repairman: 1")

    env = Environment()
    warehouse = Factory(env, repairman=1)
    env.process(warehouse.initialize())
    env.run(1000)

    total = 0
    for machine in warehouse.machines:
        print(f"machine {machine.name} produced {machine.parts_produced}")
        total += machine.parts_produced
    print(f"total produced: {total}")
    with open(r"./logs/logs_repairman_1.json", mode="w+", encoding="utf-8") as log_file:
        json.dump({"logs": env.task_logs}, log_file, cls=EnhancedJSONEncoder)

    print("=== machine: 3, repairman: 2")

    env = Environment()
    warehouse = Factory(env, repairman=2)
    env.process(warehouse.initialize())
    env.run(1000)

    total = 0
    for machine in warehouse.machines:
        print(f"machine {machine.name} produced {machine.parts_produced}")
        total += machine.parts_produced
    print(f"total produced: {total}")
    with open(r"./logs/logs_repairman_2.json", mode="w+", encoding="utf-8") as log_file:
        json.dump({"logs": env.task_logs}, log_file, cls=EnhancedJSONEncoder)

    print("=== machine: 3, repairman: 3")

    env = Environment()
    warehouse = Factory(env, repairman=3)
    env.process(warehouse.initialize())
    env.run(1000)

    total = 0
    for machine in warehouse.machines:
        print(f"machine {machine.name} produced {machine.parts_produced}")
        total += machine.parts_produced
    print(f"total produced: {total}")
    with open(r"./logs/logs_repairman_3.json", mode="w+", encoding="utf-8") as log_file:
        json.dump({"logs": env.task_logs}, log_file, cls=EnhancedJSONEncoder)


if __name__ == "__main__":
    test_machine()
