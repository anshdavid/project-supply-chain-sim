def calc_task_progress(start: int, end: int, actual_end: int) -> float:
    """
    Returns task progress as a percentage (0 to 100), capped at 100%.
    """
    assert start <= end, "Start time must be less than or equal to end time."
    assert start <= actual_end <= end, "Actual end time must be between start and end times."

    duration = end - start
    if duration <= 0:
        return 0.0
    progress = ((actual_end - start) / duration) * 100
    progress = max(0.0, min(progress, 100.0))  # Clamp between 0 and 100
    return round(progress, 2)
