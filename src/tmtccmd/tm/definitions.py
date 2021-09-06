import enum
from typing import Deque, Tuple, List, Union
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface

TelemetryListT = List[bytearray]
TelemetryQueueT = Deque[bytearray]

PusTmQueue = Deque[PusTelemetry]
PusTmTupleT = Tuple[bytearray, PusTelemetry]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]
PusIFListT = List[Union[PusTmInfoInterface, PusTmInterface]]
PusIFQueueT = Deque[PusIFListT]

PusTmListT = List[PusTelemetry]
PusTmObjQeue = Deque[PusTelemetry]
PusTmTupleQueueT = Deque[PusTmTupleT]


class TmTypes(enum.Enum):
    NONE = enum.auto()
    CCSDS_SPACE_PACKETS = enum.auto()
