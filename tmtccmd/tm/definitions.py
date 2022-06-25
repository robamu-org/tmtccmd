from typing import Deque, List, Union
from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface

TelemetryListT = List[bytes]
TelemetryQueueT = Deque[bytes]

PusTmQueue = Deque[PusTelemetry]
PusTmListT = List[PusTelemetry]

PusTmQueueT = Deque[PusTmListT]
PusIFListT = List[Union[PusTmInfoInterface, PusTmInterface]]
PusIFQueueT = Deque[PusIFListT]
