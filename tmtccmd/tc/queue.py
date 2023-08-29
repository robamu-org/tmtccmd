from __future__ import annotations

import abc
from abc import ABC
from collections import deque
from datetime import timedelta
from enum import Enum
from typing import Optional, Deque, cast, Any, Type


from spacepackets.ccsds import SpacePacket
from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss import PusVerificator, PusService, check_pus_crc
from tmtccmd.tc.procedure import TcProcedureBase, DefaultProcedureInfo
from tmtccmd.util import ProvidesSeqCount
from tmtccmd.pus import Pus11Subservices


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
    def __init__(self, base: Optional[TcQueueEntryBase]):
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

    def to_space_packet_entry(self) -> SpacePacketEntry:
        return self.__cast_internally(SpacePacketEntry, TcQueueEntryType.CCSDS_TC)

    def to_raw_tc_entry(self) -> RawTcEntry:
        return self.__cast_internally(RawTcEntry, TcQueueEntryType.RAW_TC)

    def to_wait_entry(self) -> WaitEntry:
        return self.__cast_internally(WaitEntry, TcQueueEntryType.WAIT)

    def to_packet_delay_entry(self) -> PacketDelayEntry:
        return self.__cast_internally(PacketDelayEntry, TcQueueEntryType.PACKET_DELAY)


class QueueWrapper:
    def __init__(
        self,
        info: TcProcedureBase,
        queue: QueueDequeT,
        inter_cmd_delay: timedelta = timedelta(milliseconds=0),
    ):
        self.info = info
        self.queue = queue
        self.inter_cmd_delay = inter_cmd_delay

    @classmethod
    def empty(cls):
        return cls(DefaultProcedureInfo.empty(), deque())

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

    def empty(self) -> bool:
        return len(self.queue_wrapper.queue) == 0

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
    """Default PUS Queue Helper which simplifies inserting PUS telecommands
    into the queue. It also provides a way to optionally stamp common PUS TC fields which would
    otherwise add boilerplate code during the packet creation process. This includes the following
    packet properties and it is also able to add the telecommand into a provided PUS verificator.

    This queue helper also has special support for PUS 11 time tagged PUS telecommands and will
    perform its core functionality for the time-tagged telecommands as well.
    """

    def __init__(
        self,
        queue_wrapper: QueueWrapper,
        tc_sched_timestamp_len: int,
        seq_cnt_provider: Optional[ProvidesSeqCount],
        pus_verificator: Optional[PusVerificator],
        default_pus_apid: Optional[int],
    ):
        """
        :param queue_wrapper: Queue Wrapper. All entries are inserted here
        :param default_pus_apid: Default APID which will be stamped onto all provided PUS TC packets
        :param seq_cnt_provider: The sequence count will be stamped onto all provided PUS TC packets
        :param pus_verificator: All provided PUS TCs will be added to this verificator
        """
        super().__init__(queue_wrapper)
        self.seq_cnt_provider = seq_cnt_provider
        self.pus_verificator = pus_verificator
        self.pus_apid = default_pus_apid
        self.tc_sched_timestamp_len = tc_sched_timestamp_len

    def pre_add_cb(self, entry: TcQueueEntryBase):
        if entry.etype == TcQueueEntryType.PUS_TC:
            pus_entry = cast(PusTcEntry, entry)
            if (
                pus_entry.pus_tc.service == PusService.S11_TC_SCHED
                and pus_entry.pus_tc.subservice == Pus11Subservices.TC_INSERT
            ):
                self._handle_time_tagged_tc(pus_entry.pus_tc)
            self._pus_packet_handler(pus_entry.pus_tc)

    def _handle_time_tagged_tc(self, pus_tc: PusTelecommand):
        pus_tc_raw = pus_tc.app_data[self.tc_sched_timestamp_len :]
        if not check_pus_crc(pus_tc_raw):
            raise ValueError(
                f"crc check on contained PUS TC with length {len(pus_tc_raw)} failed"
            )
        time_tagged_tc = PusTelecommand.unpack(pus_tc_raw)
        self._pus_packet_handler(time_tagged_tc)
        pus_tc.app_data[self.tc_sched_timestamp_len :] = time_tagged_tc.pack()

    def _pus_packet_handler(self, pus_tc: PusTelecommand):
        recalc_crc = False
        if self.pus_apid is not None:
            recalc_crc = True
            pus_tc.apid = self.pus_apid
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
