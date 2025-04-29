from dataclasses import dataclass, is_dataclass, asdict
import json
from typing import Literal


@dataclass
class EventLog:
    event_id: str
    event_name: str
    event_type: Literal["episode", "job"]
    event_start_timestamp: float | int
    event_lenght: float | int | None = None
    event_end_timestamp: float | int | None = None


@dataclass
class TaskLog:
    task_id: str
    task_name: str
    task_events: list[EventLog]


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)  # type:ignore
        return super().default(o)
