from typing import Tuple, Union, Deque
from tmtccmd.config.definitions import QueueCommands
from tmtccmd.ecss.tc import PusTcTupleT, PusTelecommand

TcAuxiliaryTupleT = Tuple[QueueCommands, any]
TcQueueEntryT = Union[TcAuxiliaryTupleT, PusTcTupleT]
PusTcTupleT = Tuple[bytearray, Union[PusTelecommand]]
TcQueueT = Deque[TcQueueEntryT]
