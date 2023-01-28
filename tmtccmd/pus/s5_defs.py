import dataclasses
from typing import Optional, Dict

from spacepackets.ecss.pus_5_event import Severity


def str_to_severity(string: str) -> Optional[Severity]:
    if string == "INFO":
        return Severity.INFO
    elif string == "LOW":
        return Severity.LOW
    elif string == "MEDIUM":
        return Severity.MEDIUM
    elif string == "HIGH":
        return Severity.HIGH


@dataclasses.dataclass
class EventInfo:
    id: int = 0
    name: str = ""
    severity: str = ""
    info: str = ""
    file_location: str = ""


EventDictT = Dict[int, EventInfo]
