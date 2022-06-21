from __future__ import annotations
from enum import Enum
from typing import Deque
from typing import cast
from spacepackets.ecss.tc import PusTelecommand


class TcQueueEntryType(Enum):
    PUS_TC = "pus-tc"
    RAW_TC = "raw-tc"
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
        super().__init__(TcQueueEntryType.PUS_TC)
        self.pus_tc = pus_tc

    def __repr__(self):
        return f"{self.__class__.__name__}(pus_tc={self.pus_tc!r}"


class LogQueueEntry(TcQueueEntryBase):
    def __init__(self, log_str: str):
        super().__init__(TcQueueEntryType.PRINT)
        self.print_str = log_str

    def __repr__(self):
        return f"{self.__class__.__name__}(print_str={self.print_str!r}"


class RawTcEntry(TcQueueEntryBase):
    def __init__(self, tc: bytes):
        super().__init__(TcQueueEntryType.RAW_TC)
        self.tc = tc

    def __repr__(self):
        return f"{self.__class__.__name__}(tc={self.tc!r}"


class WaitEntry(TcQueueEntryBase):
    def __init__(self, wait_secs: float):
        super().__init__(TcQueueEntryType.WAIT)
        self.wait_time = wait_secs

    def __repr__(self):
        return f"{self.__class__.__name__}(wait_time={self.wait_time!r}"


class TimeoutEntry(TcQueueEntryBase):
    def __init__(self, timeout_secs: float):
        super().__init__(TcQueueEntryType.SET_TIMEOUT)
        self.timeout_secs = timeout_secs

    def __repr__(self):
        return f"{self.__class__.__name__}(timeout_secs={self.timeout_secs!r}"


def cast_print_entry_from_base(base: TcQueueEntryBase) -> LogQueueEntry:
    return cast(LogQueueEntry, base)


def cast_pus_tc_entry_from_base(base: TcQueueEntryBase) -> PusTcEntry:
    return cast(PusTcEntry, base)


def cast_raw_tc_entry_from_base(base: TcQueueEntryBase) -> RawTcEntry:
    return cast(RawTcEntry, base)


def cast_wait_entry_from_base(base: TcQueueEntryBase) -> WaitEntry:
    return cast(WaitEntry, base)


def cast_timeout_entry_from_base(base: TcQueueEntryBase) -> TimeoutEntry:
    return cast(TimeoutEntry, base)


class ProcedureInfo:
    def __init__(self, service: str, op_code: str):
        self.service = service
        self.op_code = op_code

    def __repr__(self):
        return f"CmdInfo(service={self.service!r}, op_code={self.op_code!r}"
