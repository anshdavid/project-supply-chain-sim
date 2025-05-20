from pprint import pprint
import random
from src.machine import QMachine
from src.environment import QEnvironment


random.seed(120)

env = QEnvironment()
machine = QMachine(name="M1", env=env, mean_operation_time=10, sigma_operation=2, mttf=100000)

env.process(machine.produce_p(10))
env.run(1000)

pprint(machine.machine_state.logs)
