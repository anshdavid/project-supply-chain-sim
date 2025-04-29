import json
import random
from src.manufacturer import Factory
from src.environment import Environment
from src.schema import EnhancedJSONEncoder


random.seed(10)
env = Environment()

warehouse = Factory(env)
env.process(warehouse.initialize())

env.run(1000)
for machine in warehouse.machines:
    print(f"machine {machine.name} produced {machine.parts_produced}")

with open("./test/logs.json", "w") as l:
    json.dump({"logs": env.task_logs}, l, cls=EnhancedJSONEncoder)
