def calc_task_progress(
    task_start_time: int | float, task_duration: int | float, task_actual_end_time: int | float
) -> float:
    """
    Calculates the progress of a task as a float between 0.0 and 100.0.

    Args:
        task_start_time (int | float): The start time of the task.
        task_duration (int | float): The expected duration of the task.
        task_actual_end_time (int | float): The current or actual end time of the task.

    Returns:
        float: The progress of the task, clamped between 0.0 (not started) and 100.0 (completed).

    Edge Cases:
        - If task_duration is less than or equal to 0, returns 100.0 if the actual end time is after or at the start time, otherwise returns 0.0.
    """

    diff = (task_actual_end_time - task_start_time) / 1000
    # print(f"{task_start_time=}, {task_duration=}, {task_actual_end_time=}, {diff=}")

    if not task_actual_end_time >= task_start_time:
        raise ValueError("Actual end time must be greater than or equal to start time")

    if task_duration <= 0:
        raise ValueError("Task duration must be greater than 0")
        # return 100.0 if task_actual_end_time >= task_start_time else 0.0  # Edge case

    progress = diff / task_duration

    return round(max(0.0, min(1.0, progress)) * 100, 2)
