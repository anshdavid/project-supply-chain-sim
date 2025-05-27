from __future__ import annotations

from typing import Literal, ClassVar, TYPE_CHECKING
from datetime import datetime

import threading

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.factory import QFactory
    from src.machine import QMachine
    from src.repairman import QRepairman


class QLogEntry(BaseModel):
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


def dump_state(QFactory: QFactory) -> dict:
    return {
        "factory_state": QFactory.state.model_dump(),
        "machine_state": [
            m.state.model_dump(exclude={"logs"}) for m in QFactory._actors if m.__class__.__name__ == "QMachine"
        ],
        "repairman_state": [
            r.state.model_dump(exclude={"logs"}) for r in QFactory._actors if r.__class__.__name__ == "QRepairman"
        ],
    }
