import enum
from typing import Deque, Tuple, List, Union
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface, PusTelemetryExtended

TelemetryListT = List[bytearray]
TelemetryQueueT = Deque[bytearray]

PusTmQueue = Deque[PusTelemetryExtended]
PusTmTupleT = Tuple[bytearray, PusTelemetryExtended]

PusTmListT = List[PusTelemetryExtended]
PusTmQueueT = Deque[PusTmListT]
PusIFListT = List[Union[PusTmInfoInterface, PusTmInterface]]
PusIFQueueT = Deque[PusIFListT]

PusTmListT = List[PusTelemetryExtended]
PusTmObjQeue = Deque[PusTelemetryExtended]
PusTmTupleQueueT = Deque[PusTmTupleT]


class TmTypes(enum.Enum):
    NONE = enum.auto()
    CCSDS_SPACE_PACKETS = enum.auto()
