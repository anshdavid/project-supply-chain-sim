"""
logs.py
-------
Defines generic log entry models for use in simulation components (factory, machine, etc).

Classes:
    LogEntry: Base log entry model with timestamp, message, and optional data.
"""

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """
    Represents a generic log entry with a timestamp, message, and optional data.
    Attributes:
        timestamp (float): The simulation time when the log entry was created.
        message (str): The log message.
        data (dict): Optional additional data related to the log event.
    """

    timestamp: float
    message: str = Field(description="Log message")
    data: dict = Field(default_factory=dict, description="Additional data related to the log")
