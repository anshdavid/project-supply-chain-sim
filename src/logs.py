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

from typing import Literal, ClassVar, TYPE_CHECKING
from datetime import datetime

import threading

from pydantic import BaseModel, Field


if TYPE_CHECKING:
    from src.factory import QFactory


class QLogEntry(BaseModel):
    """
    Schema for a timeline item/log entry compatible with vis-timeline's item properties.
    The 'id' field autoincrements from 1 by default.
    """

    _counter: ClassVar[int] = 1
    _lock: ClassVar[threading.Lock] = threading.Lock()

    id: int | str | None = Field(
        default=None,
        description="An id for the item. Using an id is not required but highly recommended. An id is needed when dynamically adding, updating, and removing items in a DataSet.",
    )

    type: Literal["box", "point", "range", "background"] = Field(
        description="The type of the item. Can be 'box' (default), 'point', 'range', or 'background'. Types 'box' and 'point' need a start date, the types 'range' and 'background' needs both a start and end date.",
    )

    content: str = Field(description="The contents of the item. Can be plain text or HTML code.")

    start: str = Field(description="ISO8601 format, e.g. '2025-05-25T19:45:49'")

    end: str | None = Field(default=None, description="ISO8601 format, e.g. '2025-05-25T19:45:49'")

    editable: bool = Field(
        default=False,
        description="If true, the item can be edited by the user. If false, the item is not editable.",
    )

    selectable: bool = Field(
        default=True,
        description="If true, the item can be selected by the user. If false, the item is not selectable.",
    )

    group: None | str = Field(default=None, description="The group to which the item belongs (optional).")

    className: None | Literal["expected"] = Field(
        default=None, description="A className can be used to give items an individual css style. "
    )

    tooltip: None | str = Field(default=None, description="A tooltip can be used to give items an individual tooltip.")

    @classmethod
    def make_task(
        cls,
        start: int,
        end: int,
        content: str,
        group: str,
        id_: int | str | None = None,
        class_name: None | Literal["expected"] = None,
    ) -> QLogEntry:
        # fmt: off
        return QLogEntry(
            id=id_, group=group, type="range", content=content, start=datetime.fromtimestamp(start).isoformat(), end=datetime.fromtimestamp(end).isoformat(), className=class_name
        )  # fmt: on

    @classmethod
    def make_event(cls, start: int, content: str, group: str, id_: int | str | None = None) -> QLogEntry:
        # fmt: off
        return QLogEntry(
            id=id_, group=group, type="point", content=content, start=datetime.fromtimestamp(start).isoformat(), end=None, editable=False, selectable=False
        )  # fmt: on

    @classmethod
    def make_marker(cls, *args, **kwargs) -> QLogEntry | None:
        _ = 1


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

        factory_logs = {factory.state.name: list(factory.state.logs)}
        machine_logs = {m.state.name: list(m.state.logs) for m in factory.state.get_machine_store().items}
        repairman_logs = {r.state.name: list(r.state.logs) for r in factory.state.get_repairman_store().items}

        return cls(
            launch_timestamp=launch_timestamp,
            simulation_duration=simulation_duration,
            simulation_runtime=simulation_runtime,
            description=description,
            factory_logs=factory_logs,
            machine_logs=machine_logs,
            repairman_logs=repairman_logs,
        )

    def viz_dump(self, log_events: bool = False) -> dict:
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
        NEXT_GROUP_ID = 1
        LOG_EVENTS = log_events

        def process(logs: list[QLogEntry], entity_name: str):

            nonlocal NEXT_GROUP_ID
            if entity_name not in group_map:
                group_map[entity_name] = NEXT_GROUP_ID
                groups.append({"id": NEXT_GROUP_ID, "content": entity_name})
                NEXT_GROUP_ID += 1

            for log in logs:
                data.append(log.model_dump())

                if not LOG_EVENTS and log.type == "point":
                    continue

                log.group = str(group_map[entity_name])
                data.append(log.model_dump())

        # Process all logs
        for fac, logs in dict(self.factory_logs).items():
            process(logs, fac)
        for mach, logs in dict(self.machine_logs).items():
            process(logs, mach)
        for rep, logs in dict(self.repairman_logs).items():
            process(logs, rep)

        return {"data": data, "groups": groups}
