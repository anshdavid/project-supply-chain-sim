import simpy
from src.machine import Machine
from src.environment import Environment, EventHandler, EventLog
from src import shortuuid


class Repairman(simpy.Resource):

    # fmt:off
    def __init__(
        self, env: Environment, capacity: int = 3, time_to_repair: float = 30, 
        downtime: float = 1.5
    ):  # fmt:on
        super().__init__(env, capacity)
        self.env = env
        self.time_to_repair = time_to_repair
        self.downtime = downtime

        self.task_id = shortuuid.uuid()
        self.task_name = f"Task Repair"
        EventHandler.create_task(self.env.task_logs, self.task_id, self.task_name)

    def start_repair(self, machine: Machine):
        with self.request() as req:
            yield req
            EventHandler.add_event_to_task(
                self.env.task_logs,
                self.task_id,
                EventLog(
                    shortuuid.uuid(),
                    f"machine-{machine.name}-repair-start",
                    "episode",
                    self.env.now,
                ),
            )
            yield self.env.timeout(self.time_to_repair)
            EventHandler.add_event_to_task(
                self.env.task_logs,
                self.task_id,
                EventLog(
                    shortuuid.uuid(),
                    f"machine-{machine.name}-repaired",
                    "episode",
                    self.env.now,
                ),
            )
            machine.machine_reset_start()
            yield self.env.timeout(self.downtime)
