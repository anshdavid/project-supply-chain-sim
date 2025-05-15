import random
from typing import Callable, Literal

from pydantic import BaseModel, Field

from src.environment import Environment, EventHandler, EventLog
from src import shortuuid


class MachineState(BaseModel):

    name: str
    state: Literal["idle", "working", "broken", "waiting_repair"] = Field(
        ..., description="Current operational state: idle, working, broken, waiting_repair"
    )
    mean_operation_time: float = Field(..., description="Mean time per part")
    sigma: float = Field(..., description="Standard deviation in operation time")
    mtbf: float = Field(..., description="Mean Time Between Failures")
    failure_event_due: float | None = Field(None, description="Scheduled time of next failure (if known)")

    part_id: str | None = Field(None, description="ID of the part currently being produced")
    acquire_resource: function | None = Field(None, description="Identifier or name of the resource pool")
    part_requested_queue: str | None = Field(None, description="Identifier or name of the shared queue source")
    part_produced_queue: int = Field(0, description="Total parts successfully produced by this machine")


class Machine:
    @staticmethod
    def time_per_part(mean_operation_time: float, sigma_operation: float, fixed_time=False):
        """
        Calculates the operation time per part, either as a fixed value or sampled from a normal distribution.
        Args:
            mean_operation_time (float): The mean operation time for producing a part.
            sigma_operation (float): The standard deviation of the operation time.
            fixed_time (bool, optional): If True, returns the mean operation time as a fixed value. If False, samples from a normal distribution. Defaults to False.
        Returns:
            float: The operation time for a part. If sampling, ensures the value is positive.
        """

        if fixed_time:
            return mean_operation_time

        t = random.normalvariate(mean_operation_time, sigma_operation)
        while t <= 0:
            t = random.normalvariate(mean_operation_time, sigma_operation)
        return t

    @staticmethod
    def ttf(mean_time_to_failure: float):
        """
        Calculates the time to failure based on the mean time to failure (MTTF) using an exponential distribution.

        Args:
            mean_time_to_failure (float): The mean time to failure (MTTF) parameter for the exponential distribution.

        Returns:
            float: A randomly generated time to failure.

        Raises:
            ValueError: If mean_time_to_failure is not positive.

        Note:
            This function requires the 'random' module to be imported.
        """
        return 1 / random.expovariate(mean_time_to_failure)

    # fmt:off
    def __init__(self, name: str, env: Environment, mean_operation_time: float = 20., sigma_operation: float = 2., mean_time_to_failure: float = 100., repair_callback: Callable = lambda x: None):  # fmt:on

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
