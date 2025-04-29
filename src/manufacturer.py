from src.machine import Machine
from src.environment import Environment
from src.repairman import Repairman


class Factory:
    def __init__(self, env: Environment, machines: int = 3, repairman: int = 1):
        self.env = env
        self.machines = [
            Machine(f"machine:{i}", env, repair_callback=self.trigger_repair)
            for i in range(machines)
        ]
        self.repairman = Repairman(self.env, repairman)

    def initialize(self):
        for m in self.machines:
            self.env.process(m.produce())
        yield self.env.timeout(0)

    def trigger_repair(self, machine: Machine):
        self.env.process(self.repairman.start_repair(machine))
