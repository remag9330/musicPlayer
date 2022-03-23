from typing import Tuple

def secs_to_hours_mins_secs(total_secs: float) -> Tuple[int, int, int]:
    secs = int(total_secs % 60)
    total_secs -= secs

    mins = int((total_secs / 60) % 60)
    total_secs -= mins * 60

    hours = int(total_secs / (60 * 60))

    return (hours, mins, secs)

def hours_mins_secs_to_human_readable(hms: Tuple[int, int, int]) -> str:
    (hours, mins, secs) = hms
    if hours > 0:
        return f"{hours}:{mins:02}:{secs:02}"
    else:
        return f"{mins:02}:{secs:02}"