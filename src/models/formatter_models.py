from enum import Enum

class FormatterPlanResult(Enum):
    OK = "ok"
    SKIP = "skip"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
