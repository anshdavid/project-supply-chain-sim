from __future__ import annotations
import simpy

from src.schema import EventLog, TaskLog


class EventHandler:

    @staticmethod
    def get_task_by_id(task_list: list[TaskLog], task_id: str) -> TaskLog | None:
        return next((task for task in task_list if task.task_id == task_id), None)

    @staticmethod
    def get_event_by_id(
        task_list: list[TaskLog], event_id: str, task_id: str | None = None
    ) -> EventLog | None:
        if task_id:
            if task := EventHandler.get_task_by_id(task_list, task_id):
                return next(
                    (event for event in task.task_events if event.event_id == event_id),
                    None,
                )
            return None
        else:
            return next(
                (
                    event
                    for task in task_list
                    for event in task.task_events
                    if event.event_id == event_id
                ),
                None,
            )

    @staticmethod
    def create_task(task_list: list[TaskLog], task_id: str, task_name: str) -> TaskLog:
        task = EventHandler.get_task_by_id(task_list, task_id)
        if task is None:
            task = TaskLog(task_id=task_id, task_name=task_name, task_events=[])
            task_list.append(task)
        return task

    @staticmethod
    def add_event_to_task(task_list: list[TaskLog], task_id: str, event: EventLog):
        task = EventHandler.get_task_by_id(task_list, task_id)
        if task is None:
            task = EventHandler.create_task(task_list, task_id, f"Task {task_id}")
        task.task_events.append(event)

    @staticmethod
    def update_event(task_list: list[TaskLog], task_id: str, event_id: str, **updates):
        if event := EventHandler.get_event_by_id(task_list, event_id, task_id):
            for key, value in updates.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            return event
        return None


class Environment(simpy.Environment):

    def __init__(self, initial_time: int | float = 0):
        super().__init__(initial_time)
        self._task_logs: list[TaskLog] = []

    @property
    def task_logs(self) -> list[TaskLog]:
        return self._task_logs
