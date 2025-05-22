"""
logs.py
-------
Defines log entry models for use in simulation components such as factories, machines, repairmen, and the overall simulation.

Classes:
    QLogEntry: Represents individual log entries for events and tasks in the simulation.
    QSimulationLog: Aggregates simulation-level logs, including factory, machine, and repairman logs, and provides a unified structure for simulation event tracking.

Usage:
    Use QLogEntry to represent individual events or tasks in the simulation.
    Use QSimulationLog to aggregate and manage logs across the entire simulation.
"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from datetime import datetime

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.factory import QFactory


class QLogEntry(BaseModel):
    """
    Represents a generic log entry for simulation events.

    Attributes:
        timestamp (int | float): The simulation time when the log entry was created, in seconds since epoch.
        duration (int | float): Duration of the simulation event, 0 if type_ is "Event", > 0 if type_ is "Task".
        type_ (Literal["Event", "Task"]): Type of log entry (default: "Event").
        message (str): The log message describing the event or task.
        data (dict): Optional additional data related to the log event (default: empty dict).
    """

    timestamp: int | float  # Accept both float (sim time) and str (UTC ISO8601)
    duration: int | float = Field(default=0, description="Duration of the log entry")
    type_: Literal["Event", "Task", "Marker"] = Field(default="Event", description="Type of log entry")
    message: str = Field(description="Log message")
    data: dict = Field(default_factory=dict, description="Additional data related to the log")

    @classmethod
    def make_task(
        cls, timestamp: int | float, duration: int | float, message: str, data: dict | None = None
    ) -> QLogEntry:
        """
        Create a log entry of type "Task".

        Args:
            timestamp (int | float): The simulation time when the log entry was created.
            duration (int | float): Duration of the task.
            message (str): The log message describing the task.
            data (dict, optional): Additional data related to the task.

        Returns:
            QLogEntry: A log entry of type "Task".
        """
        return cls(timestamp=timestamp, duration=duration, type_="Task", message=message, data=data or {})

    @classmethod
    def make_event(cls, timestamp: int | float, message: str, data: dict | None = None) -> QLogEntry:
        """
        Create a log entry of type "Event".

        Args:
            timestamp (int | float): The simulation time when the log entry was created.
            message (str): The log message describing the event.
            data (dict, optional): Additional data related to the event.

        Returns:
            QLogEntry: A log entry of type "Event".
        """
        return cls(timestamp=timestamp, duration=0, type_="Event", message=message, data=data or {})

    @classmethod
    def make_marker(cls, timestamp: int | float, message: str, data: dict | None = None) -> QLogEntry:
        """
        Create a log entry of type "Marker".

        Args:
            timestamp (int | float): The simulation time when the log entry was created.
            message (str): The log message describing the marker.
            data (dict, optional): Additional data related to the marker.

        Returns:
            QLogEntry: A log entry of type "Marker".
        """
        return cls(timestamp=timestamp, duration=0, type_="Marker", message=message, data=data or {})


class QSimulationLog(BaseModel):
    """
    Represents a log entry for the overall simulation, aggregating logs from factories, machines, and repairmen.

    Attributes:
        launch_timestamp (str): Launch timestamp of the simulation in ISO8601 format.
        simulation_duration (int): Duration of the simulation in seconds.
        simulation_runtime (int | float): Runtime of the simulation in seconds.
        description (str): Description of the simulation.
        factory_logs (dict[str, list[QLogEntry]]): Mapping of factory names to their log entries.
        machine_logs (dict[str, list[QLogEntry]]): Mapping of machine names to their log entries.
        repairman_logs (dict[str, list[QLogEntry]]): Mapping of repairman names to their log entries.

    Methods:
        from_factory: Creates a QSimulationLog instance from a QFactory instance, aggregating logs from the factory, its machines, and repairmen.
        anychart_dump: Converts the simulation logs into a format compatible with AnyChart visualizations.
        viz_dump: Converts the simulation logs into a format compatible with timeline visualizations.
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
            m.machine_state.name: list(m.machine_state.logs) for m in factory.factory_state.get_machine_store().items
        }
        repairman_logs = {
            r.repairman_state.name: list(r.repairman_state.logs)
            for r in factory.factory_state.get_repairman_store().items
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

    def anychart_dump(self) -> list:
        """
        Converts the simulation logs into a format compatible with AnyChart visualizations.

        Returns:
            list: A list of nodes representing the simulation logs in AnyChart format.
        """
        nodes = []

        # Helper to build node
        def make_node(node_id, node_name, logs: list[QLogEntry]):
            tasks = []
            events = []
            for idx, log in enumerate(logs):
                if log.type_ == "Task":
                    start = log.timestamp
                    # duration is in seconds, convert to ms, add to timestamp, get end date
                    end_ms = log.timestamp + int(log.duration * 1000)
                    end = end_ms
                    tasks.append({"id": f"{node_id}_task_{idx + 1}", "start": start, "end": end})
                elif log.type_ == "Event":
                    # Map message to marker type if you want, default to "diamond"
                    marker_type = log.data.get("marker_type", "diamond")
                    fill = log.data.get("fill", "#ffa000")
                    events.append({"value": (log.timestamp), "type": marker_type, "fill": fill})

            children = []
            if tasks:
                children.append({"id": f"{node_id}_tasks", "name": "Tasks", "periods": tasks})
            if events:
                children.append({"id": f"{node_id}_events", "name": "Events", "markers": events})

            return {"id": node_id, "name": node_name, "children": children}

        # Factory nodes
        for factory, logs in dict(self.factory_logs).items():
            nodes.append(make_node(factory, factory, logs))

        # Machine nodes
        for machine, logs in dict(self.machine_logs).items():
            nodes.append(make_node(machine, machine, logs))

        # Repairman nodes
        for repairman, logs in dict(self.repairman_logs).items():
            nodes.append(make_node(repairman, repairman, logs))

        return nodes

    def viz_dump(self, include_events: bool = False) -> dict:
        """
        Converts the simulation logs into a format compatible with timeline visualizations.

        Args:
            include_events (bool): Whether to include event logs in the visualization (default: False).

        Returns:
            dict: A dictionary containing 'data' and 'groups' for timeline visualization.
        """
        data = []
        groups = []
        group_map = {}  # name to group id
        next_group_id = 1
        item_id = 1
        include_events = include_events

        def add_group(name):
            nonlocal next_group_id
            if name not in group_map:
                group_map[name] = next_group_id
                groups.append({"id": next_group_id, "content": name})
                next_group_id += 1
            return group_map[name]

        # Helper to flatten and collect
        def process(logs: list[QLogEntry], entity_name: str):
            nonlocal item_id
            nonlocal include_events
            gid = add_group(entity_name)
            for log in logs:
                if log.type_ == "Event" and not include_events:
                    continue
                start = datetime.fromtimestamp(log.timestamp / 1000).isoformat()
                item = {
                    "id": item_id,
                    "content": log.message,
                    "start": start,
                    "group": gid,
                }
                # Editable: make tasks editable, events readonly
                if log.type_ == "Task":
                    item["editable"] = True
                    if log.duration and float(log.duration) > 0:
                        # Calculate end date
                        end_ts = float(log.timestamp) + float(log.duration) * 1000
                        item["end"] = datetime.fromtimestamp(end_ts / 1000).isoformat()
                else:
                    item["editable"] = False
                data.append(item)
                item_id += 1

        # Process all logs
        # for fac, logs in dict(self.factory_logs).items():
        #     process(logs, fac)
        for mach, logs in dict(self.machine_logs).items():
            process(logs, mach)
        for rep, logs in dict(self.repairman_logs).items():
            process(logs, rep)

        return {"data": data, "groups": groups}
