"""
logs.py
-------
Defines log entry models for use in simulation components such as factories, machines, repairmen, and the overall simulation.

Classes:
    QLogEntry: Base log entry model for events and tasks, with timestamp, duration, type, message, and optional data.
    QSimulationLog: Aggregates simulation-level logs, including factory, machine, and repairman logs, and provides a unified structure for simulation event tracking.
"""

from typing import Literal
from pydantic import BaseModel, Field


class QLogEntry(BaseModel):
    """
    Represents a generic log entry for simulation events.

    Attributes:
        timestamp (float): The simulation time when the log entry was created.
        duration (float): Duration of the event or task (default: 0).
        type_ (Literal["Event", "Task"]): Type of log entry (default: "Event").
        message (str): The log message describing the event or task.
        data (dict): Optional additional data related to the log event (default: empty dict).
    """

    timestamp: float
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
