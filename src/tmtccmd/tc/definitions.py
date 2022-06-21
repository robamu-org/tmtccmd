from enum import Enum
from typing import Deque
from spacepackets.ecss.tc import PusTelecommand


class TcQueueEntryType(Enum):
    PUS_CMD = "pus-cmd"
    RAW_CMD = "raw-cmd"
    CUSTOM = "custom"
    PRINT = "print"
    WAIT = "wait"
    RAW_PRINT = "raw-print"
    SET_TIMEOUT = "set-timeout"


class TcQueueEntryBase:
    def __init__(self, etype: TcQueueEntryType):
        self.etype = etype


TcQueueT = Deque[TcQueueEntryBase]


class PusTcEntry(TcQueueEntryBase):
    def __init__(self, pus_tc: PusTelecommand):
        super().__init__(TcQueueEntryType.PUS_CMD)
        self.pus_tc = pus_tc


class PrintEntry(TcQueueEntryBase):
    def __init__(self, print_str: str):
        super().__init__(TcQueueEntryType.PRINT)
        self.print_str = print_str


class RawTcEntry(TcQueueEntryBase):
    def __init__(self, raw_tc: bytes):
        super().__init__(TcQueueEntryType.RAW_CMD)
        self.raw_tc = raw_tc


class ProcedureInfo:
    def __init__(self, service: str, op_code: str):
        self.service = service
        self.op_code = op_code

    def __repr__(self):
        return f"CmdInfo(service={self.service!r}, op_code={self.op_code!r}"
