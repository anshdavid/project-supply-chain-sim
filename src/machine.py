"""
machine.py
This module defines the QMachine class and related utilities for simulating a production machine within a factory environment.
It provides mechanisms for modeling machine operation, failures, repairs, and production statistics, leveraging Pydantic models
for configuration and state management. The simulation is intended to be used within a discrete-event simulation environment
(such as SimPy), and supports integration with a factory and environment context.
Main Components:
----------------
- QMachine: Simulates a production machine, tracking its operational state, production statistics, and logs.
- QMachineLog: Represents a log entry for the machine, including a timestamp, message, and optional data.
- QMachineConfig: Configuration schema for initializing a QMachine.
- QMachineState: Tracks the current state and statistics of the machine, and provides methods for state and production updates.
- Utility functions:
    - time_per_part: Calculates the operation time per part, either as a fixed value or sampled from a normal distribution.
    - mean_time_to_failure: Calculates the time to failure based on the mean time to failure (MTTF) using an exponential distribution.
------
- Use produce() to start production of parts.
- Use repair() to simulate repairs and restart() to resume operation after repair or failure.
Dependencies:
-------------
- random: For stochastic time calculations.
- pydantic: For configuration and state models.
- src.environment.QEnvironment: The simulation environment.
- src.factory.QFactory: The factory context (referenced via TYPE_CHECKING).
"""

from __future__ import annotations


import random
from typing import Literal, TYPE_CHECKING


from pydantic import BaseModel, Field, PrivateAttr

from src.environment import QEnvironment

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


def mean_time_to_failure(mttf: float, fixed_time=False):
    """
    Calculates the mean time to failure (MTTF) for a system or component.
    If `fixed_time` is True, returns the provided `mttf` value directly.
    If `fixed_time` is False, returns a random value sampled from an exponential distribution
    with the specified mean time to failure.
    Args:
        mttf (float): The mean time to failure.
        fixed_time (bool, optional): If True, return the fixed `mttf` value.
            If False, sample from an exponential distribution. Defaults to False.
    Returns:
        float: The time to failure, either as a fixed value or a random sample.
    Raises:
        ZeroDivisionError: If `mttf` is zero when `fixed_time` is False.
    """

    if fixed_time:
        return mttf

    return random.expovariate(1 / mttf)


class QMachine:
    """
    QMachine simulates a production machine within a factory environment, tracking its operational state, production statistics, and logs.
    Classes:
        QMachineLog (BaseModel):
            Represents a log entry for the machine, including a timestamp, message, and optional data.
        QMachineConfig (BaseModel):
            Configuration schema for initializing a QMachine, including name, state, mean operation time, standard deviation, and mean time to failure.
        QMachineState (BaseModel):
            Tracks the current state and statistics of the machine, such as name, state, mean operation time, sigma, mttf, parts produced, parts pending, and logs.
            Provides methods to update state, parts produced/pending, and manage references to the environment and factory.
    Methods:
        from_config(env: QEnvironment, factory: QFactory, config: QMachineConfig) -> QMachine:
            Class method to instantiate a QMachine from a configuration object.
        __init__(name: str, factory: QFactory, env: QEnvironment, mean_operation_time: float, sigma_operation: float, mttf: float):
            Initializes a QMachine with the given parameters and sets up its state and event timers.
        produce(parts_to_produce: int):
            Simulates the production of a specified number of parts, handling state transitions, production timing, and failure events.
        restart():
            Restarts the machine after a failure or repair, resuming production if there are pending parts.
        repair(timeout: float):
            Simulates the repair process by setting the machine to 'repair' state, waiting for the specified timeout, and then restarting.
    Attributes:
        machine_state (QMachine.QMachineState):
            The current state and statistics of the machine.
        event_failure:
            Event representing the next scheduled failure of the machine.
        event_production:
            Event representing the next scheduled production completion.
    Usage:
        - Instantiate QMachine using from_config or __init__.
        - Use produce() to start production.
        - Use repair() to simulate repairs.
        - Use restart() to resume operation after repair or failure.
    """

    class QMachineLog(BaseModel):
        """
        Represents a log entry for the QMachine, containing a timestamp, a message, and optional additional data.
        Attributes:
            timestamp (float): The simulation time when the log entry was created.
            message (str): The log message.
            data (dict): Optional additional data related to the log event.
        """

        timestamp: float
        message: str = Field(description="Log message")
        data: dict = Field(default_factory=dict, description="Additional data related to the log")

    class QMachineConfig(BaseModel):
        """
        Configuration model for a machine in the system.
        Attributes:
            name (str): Name of the machine.
            state (Literal): Current operational state ('idle', 'working', 'broken', 'repair').
            mean_operation_time (float): Mean time per part (must be > 0).
            sigma (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure (must be > 0).
        """

        name: str = Field(description="Name of the machine")
        state: Literal["idle", "working", "broken", "repair"] = Field(
            description="Current operational state: idle, working, broken"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(..., description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)

    class QMachineState(BaseModel):
        """
        QMachineState represents the operational state and statistics of a machine in a manufacturing environment.
        Attributes:
            name (str): Name of the machine.
            state (Literal): Current operational state ('idle', 'working', 'broken', 'repair').
            mean_operation_time (float): Mean time per part (must be > 0).
            sigma (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure (must be > 0).
            parts_produced (int): Total parts produced by the machine.
            parts_pending (int): Pending parts to be produced.
            logs (list): List of QMachineLog entries.
            timeout_event_failure (float): Timeout event for failure.
            timeout_event_production (float): Timeout event for production.
        Methods:
            set_state(state): Set the machine state and log the change.
            get_state(): Get the current state.
            is_state(state): Check if the machine is in a given state.
            update_parts_produced(parts): Increment parts produced and log.
            update_parts_pending(parts): Increment/decrement parts pending and log.
            calculate_timeout_to_failure(fixed_time): Calculate time to next failure.
            calculate_timeout_to_produce(fixed_time): Calculate time to produce a part.
            set_factory(factory): Set the associated factory and log.
            get_factory(): Get the associated factory.
            get_environment(): Get the associated environment.
        """

        name: str
        state: Literal["idle", "working", "broken", "repair"] = Field(
            description="Current operational state: idle, working, broken"
        )
        mean_operation_time: float = Field(description="Mean time per part", gt=0)
        sigma: float = Field(description="Standard deviation in operation time")
        mttf: float = Field(description="Mean Time to Failures", gt=0)
        parts_produced: int = Field(default=0, description="Total parts produced by the machine")
        parts_pending: int = Field(default=0, description="Pending parts to be produced")
        logs: list[QMachine.QMachineLog] = []
        # Field(default_factory=list, description="List of logs for the machine")

        timeout_event_failure: float = Field(default=0, description="Timeout event for failure")
        timeout_event_production: float = Field(default=0, description="Timeout event for production")

        _environment: QEnvironment = PrivateAttr()
        _factory: QFactory | None = PrivateAttr(default=None)

        def set_state(self, state: Literal["idle", "working", "broken", "repair"]):
            """
            Set the state of the machine and log the state change.

            Args:
                state (Literal["idle", "working", "broken", "repair"]): The new state to set for the machine.

            Side Effects:
                Updates the machine's state and appends a log entry with the current timestamp and state change message.
            """
            self.state = state
            self.logs.append(QMachine.QMachineLog(timestamp=self._environment.now, message=f"State changed to {state}"))

        def get_state(self) -> str:
            """
            Returns the current state of the machine.

            Returns:
                str: The current state.
            """
            return self.state

        def is_state(self, state: Literal["idle", "working", "broken", "repair"]) -> bool:
            """
            Check if the current state of the machine matches the specified state.

            Args:
                state (Literal["idle", "working", "broken", "repair"]): The state to compare against the machine's current state.

            Returns:
                bool: True if the machine's current state matches the specified state, False otherwise.
            """
            return self.state == state

        def update_parts_produced(self, parts: int):
            """
            Updates the number of parts produced by the machine.

            Args:
                parts (int): The number of parts to add to the current total.

            Side Effects:
                - Increments the `parts_produced` attribute by the specified amount.
                - Appends a log entry to the `logs` list with the current timestamp and an update message.
            """
            self.parts_produced += parts
            self.logs.append(
                QMachine.QMachineLog(
                    timestamp=self._environment.now, message=f"Parts produced updated to {self.parts_produced}"
                )
            )

        def update_parts_pending(self, parts: int):
            """
            Updates the number of parts pending by adding the specified amount.

            Args:
                parts (int): Signed (+/-) number of parts to add or subtract to the pending count.

            Side Effects:
                - Increments the `parts_pending` attribute by the given value.
                - Appends a log entry to the `logs` list with the updated pending count and current timestamp.
            """
            self.parts_pending += parts
            self.logs.append(
                QMachine.QMachineLog(
                    timestamp=self._environment.now, message=f"Parts pending updated to {self.parts_pending}"
                )
            )

        def calculate_timeout_to_failure(self, fixed_time: bool = False) -> float:
            """
            Calculates and logs the timeout duration until the next machine failure event.
            This method determines the time to the next failure event using the machine's mean time to failure (MTTF).
            It optionally uses a fixed time if specified. The calculated timeout is stored in `self.timeout_event_failure`
            and a log entry is appended with the calculated value.
            Args:
                fixed_time (bool, optional): If True, uses a fixed time for the timeout calculation. Defaults to False.
            Returns:
                float: The calculated timeout duration until the next failure event.
            """

            self.timeout_event_failure = mean_time_to_failure(self.mttf, fixed_time)
            self.logs.append(
                QMachine.QMachineLog(
                    timestamp=self._environment.now,
                    message=f"Timeout to failure calculated: {self.timeout_event_failure}",
                )
            )
            return self.timeout_event_failure

        def calculate_timeout_to_produce(self, fixed_time: bool = False) -> float:
            """
            Calculates and sets the timeout required to produce a part.
            This method computes the production timeout using the `time_per_part` function,
            based on the machine's mean operation time and standard deviation. The result is
            stored in `self.timeout_event_production` and logged for traceability.
            Args:
                fixed_time (bool, optional): If True, uses a fixed time for the calculation.
                    If False, uses a stochastic approach based on the mean and sigma.
                    Defaults to False.
            Returns:
                float: The calculated timeout value for producing a part.
            """
            self.timeout_event_production = time_per_part(self.mean_operation_time, self.sigma, fixed_time)
            self.logs.append(
                QMachine.QMachineLog(
                    timestamp=self._environment.now,
                    message=f"Timeout to produce calculated: {self.timeout_event_production}",
                )
            )
            return self.timeout_event_production

        def set_factory(self, factory: QFactory):
            """
            Sets the factory for the machine and logs the change.

            Args:
                factory (QFactory): The factory instance to associate with this machine.

            Side Effects:
                Updates the machine's internal factory reference.
                Appends a log entry to the machine's logs indicating the factory change, including a timestamp and the new factory state.
            """
            self._factory = factory
            self.logs.append(
                QMachine.QMachineLog(
                    timestamp=self._environment.now,
                    message=f"Machine {self.name} Factory set to {factory.factory_state.name}",
                )
            )

        def get_factory(self) -> QFactory | None:
            """
            Returns the associated QFactory instance if available.

            Returns:
                QFactory | None: The factory object associated with this instance, or None if not set.
            """
            return self._factory

        def get_environment(self) -> QEnvironment:
            """
            Returns the current QEnvironment instance associated with the machine.

            Returns:
                QEnvironment: The environment object currently set for this machine.
            """
            return self._environment

    @classmethod
    def from_config(cls, env: QEnvironment, config: QMachineConfig):
        """
        Creates an instance of QMachine from the provided configuration.
        Args:
            env (QEnvironment): The environment in which the machine operates.
            config (QMachineConfig): Configuration object containing machine parameters.
        Returns:
            QMachine: An instance of QMachine initialized with the provided configuration.
        """
        # fmt:off
        return cls(
            name=config.name, env=env, mean_operation_time=config.mean_operation_time, sigma_operation=config.sigma, mttf=config.mttf)
        # fmt:on

    # fmt:off
    def __init__(
        self, name: str, env: QEnvironment, mean_operation_time: float, sigma_operation: float, mttf: float
    ):  # fmt:on
        """
        Initializes a QMachine with the given parameters and sets up its state and event timers.
        Args:
            name (str): Name of the machine.
            env (QEnvironment): The simulation environment.
            mean_operation_time (float): Mean time per part.
            sigma_operation (float): Standard deviation in operation time.
            mttf (float): Mean Time to Failure.
        """

        # fmt:off
        self.machine_state: QMachine.QMachineState = QMachine.QMachineState(
            name=name, state="idle", mean_operation_time=mean_operation_time, sigma=sigma_operation, mttf=mttf, parts_produced=0
        )
        # fmt:on

        self.machine_state._environment = env

        self.machine_state.set_state("idle")

        self.event_failure = self.machine_state.get_environment().timeout(
            self.machine_state.calculate_timeout_to_failure()
        )
        self.event_production = self.machine_state.get_environment().timeout(0)

    def produce(self, parts_to_produce: int):
        """
        Simulates the production of a specified number of parts by the machine.
        Args:
            parts_to_produce (int): The number of parts the machine should produce.
        Yields:
            dict: A dictionary indicating which event (production or failure) occurred.
        Behavior:
            - Sets the machine state to "working" and initializes the number of parts pending.
            - For each part to be produced:
                - Waits for either the production of a part to complete or a failure event.
                - If production completes, updates the count of produced and pending parts.
                - If a failure occurs, sets the machine state to "broken" and exits.
            - After all parts are produced, sets the machine state to "idle".
        """

        self.machine_state.parts_pending = parts_to_produce

        for _ in range(parts_to_produce):

            self.event_production = self.machine_state.get_environment().timeout(
                self.machine_state.calculate_timeout_to_produce()
            )
            self.machine_state.set_state("working")
            yield self.event_failure | self.event_production

            if self.event_production.processed:

                self.machine_state.update_parts_produced(+1)
                self.machine_state.update_parts_pending(-1)

            elif self.event_failure.processed:
                self.machine_state.set_state("broken")
                return

        self.machine_state.set_state("idle")
        return

    def restart(self):
        """
        Restarts the machine by scheduling a failure event and resuming production if there are pending parts.
        If there are parts pending, initiates the production process for the remaining parts.
        Otherwise, sets the machine state to "idle" if not "idle".
        """
        self.event_failure = self.machine_state.get_environment().timeout(mean_time_to_failure(self.machine_state.mttf))
        if self.machine_state.parts_pending > 0:
            self.machine_state.get_environment().process(self.produce(self.machine_state.parts_pending))
        else:
            if not self.machine_state.is_state("idle"):
                self.machine_state.set_state("idle")

    def repair(self, timeout: float):
        """
        Initiates the repair process for the machine by setting its state to "repair",
        waiting for the specified timeout duration, and then restarting the machine.
        Args:
            timeout (float): The amount of time (in simulation units) to wait while the machine is being repaired.
        Yields:
            simpy.events.Timeout: An event representing the passage of time during the repair process.
        """
        self.machine_state.set_state("repair")
        yield self.machine_state.get_environment().timeout(timeout)
        self.machine_state.set_state("idle")
        self.restart()
