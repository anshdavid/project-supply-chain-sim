"""
logs.py
-------
Defines generic log entry models for use in simulation components (factory, machine, etc).

Classes:
    LogEntry: Base log entry model with timestamp, message, and optional data.
"""

from typing import Literal
from pydantic import BaseModel, Field


class QLogEntry(BaseModel):
    """
    Represents a generic log entry with a timestamp, message, and optional data.
    Attributes:
        timestamp (float): The simulation time when the log entry was created.
        message (str): The log message.
        data (dict): Optional additional data related to the log event.
    """

    timestamp: float
    duration: float = Field(default=0, description="Duration of the log entry")
    type_: Literal["Event", "Task"] = Field(default="Event", description="Type of log entry")
    message: str = Field(description="Log message")
    data: dict = Field(default_factory=dict, description="Additional data related to the log")
