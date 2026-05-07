from typing import Literal

from app.models.task import Task


FailureType = Literal["retriable", "non_retriable", "critical_path"]

_RETRIABLE_ERRORS = (TimeoutError, ConnectionError, OSError)

# HTTP status codes that indicate transient failures
_RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def classify_failure(task: Task, error: Exception) -> FailureType:
    if task.is_critical_path:
        return "critical_path"

    error_str = str(error).lower()

    if isinstance(error, _RETRIABLE_ERRORS):
        return "retriable"

    if "timeout" in error_str or "connection" in error_str:
        return "retriable"

    for code in _RETRIABLE_STATUS_CODES:
        if str(code) in error_str:
            return "retriable"

    return "non_retriable"
