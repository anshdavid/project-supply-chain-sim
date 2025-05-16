from __future__ import annotations

import random
from typing import Literal, TYPE_CHECKING


from pydantic import BaseModel, Field

from src.environment import QEnvironment
from src import shortuuid

if TYPE_CHECKING:
    from src.factory import QFactory


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


def mean_time_to_failure(mttf: float):
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
    return random.expovariate(1 / mttf)


class QMachine:
    class QMachineSchema(BaseModel):
        name: str = Field(description="Name of the machine")
        mean_operation_time: float = Field(description="Mean time per part")
        sigma: float = Field(..., description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures")

    class QMachineLog(BaseModel):
        timestamp: float

    class QMachineState(BaseModel):
        name: str
        state: Literal["idle", "working", "broken", "repair"] = Field(
            description="Current operational state: idle, working, broken"
        )
        mean_operation_time: float = Field(description="Mean time per part")
        sigma: float = Field(..., description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures")
        parts_made: int = Field(default=0, description="Total parts produced by the machine")

        logs: list[QMachine.QMachineLog] = []

        def set_idle(self):
            self.state = "idle"

        def is_idle(self) -> bool:
            return self.state == "idle"

        def set_working(self):
            self.state = "working"

        def is_working(self) -> bool:
            return self.state == "working"

        def set_broken(self):
            self.state = "broken"

        def is_broken(self) -> bool:
            return self.state == "broken"

        def set_repairing(self):
            self.state = "repair"

        def is_repairing(self) -> bool:
            return self.state == "repair"

    @classmethod
    def from_config(cls, env: QEnvironment, factory: "QFactory", config: QMachineSchema):
        # fmt:off
        return cls(
            name=config.name, factory=factory, env=env, mean_operation_time=config.mean_operation_time, sigma_operation=config.sigma, mttf=config.mttf)
        # fmt:on

    # fmt:off
    def __init__(
        self, name: str, factory: QFactory, env: QEnvironment, mean_operation_time: float, sigma_operation: float, mttf: float
    ):  # fmt:on

        self.factory: QFactory = factory
        self.env: QEnvironment = env

        # fmt:off
        self.machine_state: QMachine.QMachineState = QMachine.QMachineState(
            name=name, state="idle", mean_operation_time=mean_operation_time, sigma=sigma_operation, mttf=mttf, parts_made=0)
        # fmt:on

        self.machine_state.set_idle()
        self.event_production = self.env.timeout(0)
        self.event_failure = self.env.timeout(0)

        # self.env.process(self.start())

    def start(self):
        self.event_production = self.env.timeout(
            time_per_part(self.machine_state.mean_operation_time, self.machine_state.sigma)
        )

        self.event_failure = self.env.timeout(mean_time_to_failure(self.machine_state.mttf))

        while True:
            if self.machine_state.is_idle():
                self.machine_state.set_working()
                yield self.event_failure | self.event_production

                if self.event_production.processed:
                    self.machine_state.set_idle()
                    self.machine_state.parts_made += 1
                    self.event_production = self.env.timeout(
                        time_per_part(self.machine_state.mean_operation_time, self.machine_state.sigma)
                    )

                elif self.event_failure.processed:
                    self.machine_state.set_broken()
                    return

    def restart(self):
        self.env.process(self.start())
