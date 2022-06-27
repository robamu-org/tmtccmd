from __future__ import annotations

import enum
from enum import Enum
from typing import Deque, cast, Type, Any
from spacepackets.ccsds.spacepacket import SpacePacket
from spacepackets.ecss.tc import PusTelecommand


class TcQueueEntryType(Enum):
    PUS_TC = "pus-tc"
    CCSDS_TC = "ccsds-tc"
    RAW_TC = "raw-tc"
    CUSTOM = "custom"
    LOG = "log"
    WAIT = "wait"
    PACKET_DELAY = "set-delay"


class TcQueueEntryBase:
    """Generic TC queue entry abstraction. This allows filling the TC queue with custom objects"""

    def __init__(self, etype: TcQueueEntryType):
        self.etype = etype

    def is_tc(self) -> bool:
        """Check whether concrete object is an actual telecommand"""
        if (
            self.etype == TcQueueEntryType.PUS_TC
            or self.etype == TcQueueEntryType.RAW_TC
            or self.etype == TcQueueEntryType.CCSDS_TC
        ):
            return True
        return False


QueueDequeT = Deque[TcQueueEntryBase]


class PusTcEntry(TcQueueEntryBase):
    def __init__(self, pus_tc: PusTelecommand):
        super().__init__(TcQueueEntryType.PUS_TC)
        self.pus_tc = pus_tc

    def __repr__(self):
        return f"{self.__class__.__name__}({self.pus_tc!r})"


class SpacePacketEntry(TcQueueEntryBase):
    def __init__(self, space_packet: SpacePacket):
        super().__init__(TcQueueEntryType.CCSDS_TC)
        self.space_packet = space_packet

    def __repr__(self):
        return f"{self.__class__.__name__}({self.space_packet!r})"


class LogQueueEntry(TcQueueEntryBase):
    def __init__(self, log_str: str):
        super().__init__(TcQueueEntryType.LOG)
        self.log_str = log_str

    def __repr__(self):
        return f"{self.__class__.__name__}({self.log_str!r})"


class RawTcEntry(TcQueueEntryBase):
    def __init__(self, tc: bytes):
        super().__init__(TcQueueEntryType.RAW_TC)
        self.tc = tc

    def __repr__(self):
        return f"{self.__class__.__name__}({self.tc!r})"


class WaitEntry(TcQueueEntryBase):
    def __init__(self, wait_secs: float):
        super().__init__(TcQueueEntryType.WAIT)
        self.wait_secs = wait_secs

    def __repr__(self):
        return f"{self.__class__.__name__}({self.wait_secs!r})"


class PacketDelayEntry(TcQueueEntryBase):
    def __init__(self, delay_secs: float):
        super().__init__(TcQueueEntryType.PACKET_DELAY)
        self.delay_secs = delay_secs

    def __repr__(self):
        return f"{self.__class__.__name__}({self.delay_secs!r})"


class PacketCastWrapper:
    def __init__(self, base: TcQueueEntryBase):
        self.base = base

    def __cast_internally(
        self,
        obj_type: Type[TcQueueEntryBase],
        obj: TcQueueEntryBase,
        expected_type: TcQueueEntryType,
    ) -> Any:
        if obj.etype != expected_type:
            raise TypeError(f"Invalid object {obj} for type {self.base.etype}")
        return cast(obj_type, obj)

    def to_log_entry(self) -> LogQueueEntry:
        return self.__cast_internally(LogQueueEntry, self.base, TcQueueEntryType.LOG)

    def to_pus_tc_entry(self) -> PusTcEntry:
        return self.__cast_internally(PusTcEntry, self.base, TcQueueEntryType.PUS_TC)

    def to_raw_tc_entry(self) -> RawTcEntry:
        return self.__cast_internally(RawTcEntry, self.base, TcQueueEntryType.RAW_TC)

    def to_wait_entry(self) -> WaitEntry:
        return self.__cast_internally(WaitEntry, self.base, TcQueueEntryType.WAIT)

    def to_packet_delay_entry(self) -> PacketDelayEntry:
        return self.__cast_internally(
            PacketDelayEntry, self.base, TcQueueEntryType.PACKET_DELAY
        )

    def to_space_packet_entry(self) -> SpacePacketEntry:
        return self.__cast_internally(
            SpacePacketEntry, self.base, TcQueueEntryType.CCSDS_TC
        )


class TcProcedureType(enum.Enum):
    DEFAULT = 0
    CFDP = 1
    CUSTOM = 2


class TcProcedureBase:
    def __init__(self, ptype: TcProcedureType):
        self.ptype = ptype


class CustomProcedureInfo(TcProcedureBase):
    def __init__(self, info: any):
        super().__init__(TcProcedureType.CUSTOM)
        self.info = info

    def __repr__(self):
        return f"{self.__class__.__name__}(info={self.info!r}"


class DefaultProcedureInfo(TcProcedureBase):
    """Generic abstraction for procedures. A procedure can be a single command or a sequence
    of commands. Generally, one procedure is mapped to a specific TC queue which is packed
    during run-time"""

    def __init__(self, service: str, op_code: str):
        super().__init__(TcProcedureType.DEFAULT)
        self.service = service
        self.op_code = op_code

    def __repr__(self):
        return f"CmdInfo(service={self.service!r}, op_code={self.op_code!r}"


class ProcedureCastWrapper:
    """Cast wrapper to cast the procedure base type back to a concrete type easily"""

    def __init__(self, base: TcProcedureBase):
        self.base = base

    def __cast_internally(
        self,
        obj_type: Type[TcProcedureBase],
        obj: TcProcedureBase,
        expected_type: TcProcedureType,
    ) -> Any:
        if obj.ptype != expected_type:
            raise TypeError(f"Invalid object {obj} for type {self.base.ptype}")
        return cast(obj_type, obj)

    def to_def_procedure(self) -> DefaultProcedureInfo:
        return self.__cast_internally(
            DefaultProcedureInfo, self.base, TcProcedureType.DEFAULT
        )

    def to_custom_procedure(self) -> CustomProcedureInfo:
        return self.__cast_internally(
            CustomProcedureInfo, self.base, TcProcedureType.CUSTOM
        )
