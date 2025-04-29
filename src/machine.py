import random
from typing import Callable
from src.environment import Environment, EventHandler, EventLog
from src import shortuuid


class Machine:
    @staticmethod
    def time_per_part(mean_operation_time: float, sigma_operation: float):
        t = random.normalvariate(mean_operation_time, sigma_operation)
        while t <= 0:
            t = random.normalvariate(mean_operation_time, sigma_operation)
        return t

    @staticmethod
    def ttf(mean_time_to_failure: float):
        return 1 / random.expovariate(mean_time_to_failure)

    # fmt:off
    def __init__(
        self, name: str, env: Environment, mean_operation_time: float=20., sigma_operation: float=2., mean_time_to_failure: float=100., repair_callback:Callable = lambda x: None):  # fmt:on

        self.name: str = name
        self.env: Environment = env
        self.mean_operation_time: float = mean_operation_time
        self.sigma_operation: float = sigma_operation
        self.mean_time_to_failure: float = mean_time_to_failure

        self.repair_callback: Callable = repair_callback

        self.task_id = shortuuid.uuid()
        self.task_name = f"Task Machine {self.name}"
        EventHandler.create_task(self.env.task_logs, self.task_id, self.task_name)

        self.parts_produced: int = 0
        self.active_event_id: str = "not initialized"
        self.event_failure = self.env.timeout(0)
        self.event_production = self.env.timeout(0)

        self.create_task(init=True)

    def produce(self):
        while True:
            self.create_task()

            yield self.event_failure | self.event_production

            if self.event_failure.processed:
                EventHandler.update_event(
                    self.env.task_logs,
                    self.task_id,
                    self.active_event_id,
                    event_end_timestamp=self.env.now,
                )
                EventHandler.add_event_to_task(
                    self.env.task_logs,
                    self.task_id,
                    EventLog(
                        shortuuid.uuid(),
                        "break-down-repair-requested",
                        "episode",
                        self.env.now,
                    ),
                )
                self.repair_callback(self)
                return

            if self.event_production.processed:
                self.complete_task()
                self.create_task()

    def create_task(self, init: bool = False):
        if init or self.active_event_completed:
            self.active_event_id: str = shortuuid.uuid()

            p_ = self.time_per_part(self.mean_operation_time, self.sigma_operation)
            self.event_production = self.env.timeout(p_)

            if init:
                f_ = self.ttf(self.mean_time_to_failure)
                self.event_failure = self.env.timeout(f_)

            EventHandler.add_event_to_task(
                self.env.task_logs,
                self.task_id,
                EventLog(
                    self.active_event_id,
                    f"production-start-{self.parts_produced}",
                    "job",
                    self.env.now,
                    p_,
                ),
            )

            self.active_event_completed: bool = False

    def complete_task(self):
        self.parts_produced += 1
        self.active_event_completed = True
        EventHandler.update_event(
            self.env.task_logs,
            self.task_id,
            self.active_event_id,
            event_end_timestamp=self.env.now,
        )

    def machine_reset(self):
        EventHandler.add_event_to_task(
            self.env.task_logs,
            self.task_id,
            EventLog(shortuuid.uuid(), "machine-reset", "episode", self.env.now),
        )
        self.create_task(init=True)

    def machine_start(self):
        self.env.process(self.produce())

    def machine_reset_start(self):
        self.machine_reset()
        self.machine_start()
