import enum
from typing import Optional, Dict


class Severity(enum.IntEnum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4


def str_to_severity(string: str) -> Optional[Severity]:
    if string == "INFO":
        return Severity.INFO
    elif string == "LOW":
        return Severity.LOW
    elif string == "MEDIUM":
        return Severity.MEDIUM
    elif string == "HIGH":
        return Severity.HIGH


class Subservices(enum.IntEnum):
    INFO_EVENT = Severity.INFO
    LOW_SEVERITY_EVENT = Severity.LOW
    MEDIUM_SEVERITY_EVENT = Severity.MEDIUM
    HIGH_SEVERITY_EVENT = Severity.HIGH
    ENABLE_EVENT_REPORTING = 5
    DISABLE_EVENT_REPORTING = 6


class EventInfo:
    id: int = 0
    name: str = ""
    severity: str = ""
    info: str = ""
    file_location: str = ""


EventDictT = Dict[int, EventInfo]
