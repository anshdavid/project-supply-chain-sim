"""
logs.py
-------
Defines log entry models for use in simulation components such as factories, machines, repairmen, and the overall simulation.

Classes:
    QLogEntry: Base log entry model for events and tasks, with timestamp, duration, type, message, and optional data.
    QSimulationLog: Aggregates simulation-level logs, including factory, machine, and repairman logs, and provides a unified structure for simulation event tracking.
"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from pydantic import BaseModel, Field
import datetime

if TYPE_CHECKING:
    from src.factory import QFactory
    from src.machine import QMachine
    from src.repairman import QRepairman


class QLogEntry(BaseModel):
    """
    Represents a generic log entry for simulation events.

    Attributes:
        timestamp (float | str): The simulation time when the log entry was created, or UTC ISO8601 timestamp.
        duration (float): Duration of the event or task (default: 0).
        type_ (Literal["Event", "Task"]): Type of log entry (default: "Event").
        message (str): The log message describing the event or task.
        data (dict): Optional additional data related to the log event (default: empty dict).
    """

    timestamp: float | str  # Accept both float (sim time) and str (UTC ISO8601)
    duration: float = Field(default=0, description="Duration of the log entry")
    type_: Literal["Event", "Task"] = Field(default="Event", description="Type of log entry")
    message: str = Field(description="Log message")
    data: dict = Field(default_factory=dict, description="Additional data related to the log")


class QSimulationLog(QLogEntry):
    """
    Represents a log entry for the overall simulation, aggregating logs from factories, machines, and repairmen.

    Attributes:
        timestamp (float): Simulation time of the log entry.
        duration (float): Duration of the simulation event (default: 0).
        type_ (Literal["Simulation"]): Type of log entry (always "Simulation").
        message (str): Log message for the simulation event.
        data (dict): Additional data related to the log event.
        factory_logs (dict[str, list[QLogEntry]]): Mapping of factory names to their log entries.
        machine_logs (dict[str, list[QLogEntry]]): Mapping of machine names to their log entries.
        repairman_logs (dict[str, list[QLogEntry]]): Mapping of repairman names to their log entries.
    """

    type_: Literal["Simulation"] = Field(default="Simulation", description="Type of log entry")
    factory_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of factory logs")
    machine_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of machine logs")
    repairman_logs: dict[str, list[QLogEntry]] = Field(default_factory=dict, description="List of repairman logs")

    @classmethod
    def from_factory(
        cls, factory: QFactory, duration: float = 0.0, message: str = "Simulation log", data: dict | None = None
    ):
        """
        Create a QSimulationLog from a QFactory instance, aggregating logs from the factory, its machines, and repairmen.
        Args:
            factory (QFactory): The factory instance to aggregate logs from.
            duration (float): Duration of the simulation event.
            message (str): The log message for the simulation event.
            data (dict): Additional data for the log entry.
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
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return cls(
            timestamp=now_utc,
            duration=duration,
            message=message,
            data=data or {},
            factory_logs=factory_logs,
            machine_logs=machine_logs,
            repairman_logs=repairman_logs,
        )
