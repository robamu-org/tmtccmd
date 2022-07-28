from __future__ import annotations

import abc
from abc import ABC
from datetime import timedelta
from enum import Enum
from typing import Optional, Deque, cast, Any, Type

from spacepackets.ccsds import SpacePacket
from spacepackets.ecss import PusTelecommand, PusVerificator, PusServices
from tmtccmd.logging import get_console_logger
from tmtccmd.tc.procedure import TcProcedureBase
from tmtccmd.util import ProvidesSeqCount
from tmtccmd.pus import Pus11Subservices


LOGGER = get_console_logger()


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
    def __init__(self, wait_time: timedelta):
        super().__init__(TcQueueEntryType.WAIT)
        self.wait_time = wait_time

    @classmethod
    def from_millis(cls, millis: int) -> WaitEntry:
        return cls(timedelta(milliseconds=millis))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.wait_time!r})"


class PacketDelayEntry(TcQueueEntryBase):
    def __init__(self, delay_time: timedelta):
        super().__init__(TcQueueEntryType.PACKET_DELAY)
        self.delay_time = delay_time

    @classmethod
    def from_millis(cls, millis: int) -> PacketDelayEntry:
        return cls(timedelta(milliseconds=millis))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.delay_time!r})"


class QueueEntryHelper:
    def __init__(self, base: TcQueueEntryBase):
        self.base = base

    @property
    def is_tc(self) -> bool:
        return self.base.is_tc()

    @property
    def entry_type(self) -> TcQueueEntryType:
        return self.base.etype

    def __cast_internally(
        self,
        obj_type: Type[TcQueueEntryBase],
        expected_type: TcQueueEntryType,
    ) -> Any:
        if self.base.etype != expected_type:
            raise TypeError(f"Invalid object {self.base} for type {expected_type}")
        return cast(obj_type, self.base)

    def to_log_entry(self) -> LogQueueEntry:
        return self.__cast_internally(LogQueueEntry, TcQueueEntryType.LOG)

    def to_pus_tc_entry(self) -> PusTcEntry:
        return self.__cast_internally(PusTcEntry, TcQueueEntryType.PUS_TC)

    def to_raw_tc_entry(self) -> RawTcEntry:
        return self.__cast_internally(RawTcEntry, TcQueueEntryType.RAW_TC)

    def to_wait_entry(self) -> WaitEntry:
        return self.__cast_internally(WaitEntry, TcQueueEntryType.WAIT)

    def to_packet_delay_entry(self) -> PacketDelayEntry:
        return self.__cast_internally(PacketDelayEntry, TcQueueEntryType.PACKET_DELAY)

    def to_space_packet_entry(self) -> SpacePacketEntry:
        return self.__cast_internally(SpacePacketEntry, TcQueueEntryType.CCSDS_TC)


class QueueWrapper:
    def __init__(
        self,
        info: Optional[TcProcedureBase],
        queue: Optional[QueueDequeT],
        inter_cmd_delay: timedelta = timedelta(milliseconds=0),
    ):
        self.info = info
        self.queue = queue
        self.inter_cmd_delay = inter_cmd_delay

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(info={self.info!r}, queue={self.queue!r}, "
            f"inter_cmd_delay={self.inter_cmd_delay!r})"
        )


class QueueHelperBase(ABC):
    def __init__(self, queue_wrapper: QueueWrapper):
        self.queue_wrapper = queue_wrapper

    def __repr__(self):
        return f"{self.__class__.__name__}(queue_wrapper={self.queue_wrapper!r})"

    @abc.abstractmethod
    def pre_add_cb(self, entry: TcQueueEntryBase):
        pass

    def add_log_cmd(self, print_str: str):
        self._add_entry(LogQueueEntry(print_str))

    def add_raw_tc(self, tc: bytes):
        self._add_entry(RawTcEntry(tc))

    def add_wait(self, wait_time: timedelta):
        self._add_entry(WaitEntry(wait_time))

    def add_wait_ms(self, wait_ms: int):
        self._add_entry(WaitEntry.from_millis(wait_ms))

    def add_wait_seconds(self, wait_seconds: float):
        self._add_entry(WaitEntry(timedelta(seconds=wait_seconds)))

    def add_packet_delay(self, delay: timedelta):
        self._add_entry(PacketDelayEntry(delay))

    def add_packet_delay_ms(self, delay_ms: int):
        self._add_entry(PacketDelayEntry.from_millis(delay_ms))

    def _add_entry(self, entry: TcQueueEntryBase):
        self.pre_add_cb(entry)
        self.queue_wrapper.queue.append(entry)


class DefaultPusQueueHelper(QueueHelperBase):
    def __init__(
        self,
        queue_wrapper: Optional[QueueWrapper],
        seq_cnt_provider: Optional[ProvidesSeqCount],
        pus_verificator: Optional[PusVerificator],
        apid: Optional[int],
    ):
        super().__init__(queue_wrapper)
        self.seq_cnt_provider = seq_cnt_provider
        self.pus_verificator = pus_verificator
        self.apid = apid

    def pre_add_cb(self, entry: TcQueueEntryBase):
        if entry.etype == TcQueueEntryType.PUS_TC:
            pus_entry = cast(PusTcEntry, entry)
            if (
                pus_entry.pus_tc.service == PusServices.S11_TC_SCHED
                and pus_entry.pus_tc.subservice == Pus11Subservices.TC_INSERT
            ):
                try:
                    time_tagged_tc = PusTelecommand.unpack(
                        pus_entry.pus_tc.app_data[4:]
                    )
                    self._pus_packet_handler(time_tagged_tc)
                except ValueError as e:
                    LOGGER.warning(
                        f"Attempt of unpacking time tagged TC failed with exception {e}"
                    )
            self._pus_packet_handler(pus_entry.pus_tc)

    def _pus_packet_handler(self, pus_tc: PusTelecommand):
        recalc_crc = False
        if self.apid is not None:
            recalc_crc = True
            pus_tc.apid = self.apid
        if self.seq_cnt_provider is not None:
            recalc_crc = True
            pus_tc.seq_count = self.seq_cnt_provider.get_and_increment()
        if self.pus_verificator is not None:
            # Add TC after Sequence Count and APID stamping
            self.pus_verificator.add_tc(pus_tc)
        if recalc_crc:
            pus_tc.calc_crc()

    def add_pus_tc(self, pus_tc: PusTelecommand):
        super()._add_entry(PusTcEntry(pus_tc))

    def add_ccsds_tc(self, space_packet: SpacePacket):
        super()._add_entry(SpacePacketEntry(space_packet))
