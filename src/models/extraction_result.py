from enum import Enum

class ExtractResult(Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"
