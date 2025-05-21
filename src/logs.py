"""
logs.py
-------
Defines log entry models for use in simulation components such as factories, machines, repairmen, and the overall simulation.

Classes:
    QLogEntry: Base log entry model for events and tasks, with timestamp, duration, type, message, and optional data.
    QSimulationLog: Aggregates simulation-level logs, including factory, machine, and repairman logs, and provides a unified structure for simulation event tracking.

Usage:
    Use QLogEntry to represent individual events or tasks in the simulation.
    Use QSimulationLog to aggregate and manage logs across the entire simulation.
"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.factory import QFactory


class QLogEntry(BaseModel):
    """
    Represents a generic log entry for simulation events.

    Attributes:
        timestamp (int): The simulation time when the log entry was created, in seconds since epoch.
        duration (int): Duration of the simulation event, 0 if type_ is "Event", > 0 if type_ is "Task".
        type_ (Literal["Event", "Task"]): Type of log entry (default: "Event").
        message (str): The log message describing the event or task.
        data (dict): Optional additional data related to the log event (default: empty dict).
    """

    timestamp: int | float  # Accept both float (sim time) and str (UTC ISO8601)
    duration: int | float = Field(default=0, description="Duration of the log entry")
    type_: Literal["Event", "Task"] = Field(default="Event", description="Type of log entry")
    message: str = Field(description="Log message")
    data: dict = Field(default_factory=dict, description="Additional data related to the log")


class QSimulationLog(BaseModel):
    """
    Represents a log entry for the overall simulation, aggregating logs from factories, machines, and repairmen.

    Attributes:
        launch_timestamp (str): Launch timestamp of the simulation in ISO8601 format.
        simulation_duration (int): Duration of the simulation in seconds.
        simulation_runtime (int): Runtime of the simulation in seconds.
        description (str): Description of the simulation.
        factory_logs (dict[str, list[QLogEntry]]): Mapping of factory names to their log entries.
        machine_logs (dict[str, list[QLogEntry]]): Mapping of machine names to their log entries.
        repairman_logs (dict[str, list[QLogEntry]]): Mapping of repairman names to their log entries.

    Methods:
        from_factory: Creates a QSimulationLog instance from a QFactory instance, aggregating logs from the factory, its machines, and repairmen.
    """

    launch_timestamp: str = Field(description="Launch timestamp of the simulation")
    simulation_duration: int = Field(description="Duration of the simulation")
    simulation_runtime: int | float = Field(description="Runtime of the simulation")
    description: str = Field(description="Description of the simulation")
    factory_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of factory logs")
    machine_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of machine logs")
    repairman_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of repairman logs")

    @classmethod
    def from_factory(
        cls,
        launch_timestamp: str,
        simulation_duration: int,
        simulation_runtime: int | float,
        description: str,
        factory: QFactory,
    ) -> QSimulationLog:
        """
        Create a QSimulationLog from a QFactory instance, aggregating logs from the factory, its machines, and repairmen.

        Args:
            launch_timestamp (str): Launch timestamp of the simulation in ISO8601 format.
            simulation_duration (int): Duration of the simulation in seconds.
            simulation_runtime (int | float): Runtime of the simulation in seconds.
            description (str): Description of the simulation.
            factory (QFactory): The factory instance to aggregate logs from.

        Returns:
            QSimulationLog: An aggregated simulation log entry.
        """

        factory_logs = {factory.factory_state.name: list(factory.factory_state.logs)}
        machine_logs = {
            m.machine_state.name: list(m.machine_state.logs) for m in factory.factory_state.get_all_machines()
        }
        repairman_logs = {
            r.repairman_state.name: list(r.repairman_state.logs) for r in factory.factory_state.get_all_repairmen()
        }

        return cls(
            launch_timestamp=launch_timestamp,
            simulation_duration=simulation_duration,
            simulation_runtime=simulation_runtime,
            description=description,
            factory_logs=factory_logs,
            machine_logs=machine_logs,
            repairman_logs=repairman_logs,
        )
