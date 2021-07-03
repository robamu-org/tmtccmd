from typing import Tuple, Union, Deque
from tmtccmd.config.definitions import QueueCommands
from tmtccmd.ecss.tc import PusTelecommand

TcAuxiliaryTupleT = Tuple[QueueCommands, any]
PusTcTupleT = Tuple[bytearray, Union[None, PusTelecommand]]
TcQueueEntryT = Union[TcAuxiliaryTupleT, PusTcTupleT]
TcQueueT = Deque[TcQueueEntryT]
