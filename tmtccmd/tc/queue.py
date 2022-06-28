from datetime import timedelta
from typing import Optional

from spacepackets.ccsds.spacepacket import SpacePacket
from spacepackets.ecss import PusTelecommand
from tmtccmd.tc import (
    QueueDequeT,
    LogQueueEntry,
    PusTcEntry,
    RawTcEntry,
    WaitEntry,
    SpacePacketEntry,
    PacketDelayEntry,
    TcProcedureBase,
)


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


class QueueHelper:
    def __init__(self, queue_wrapper: QueueWrapper):
        self.queue_wrapper = queue_wrapper

    def __repr__(self):
        return f"{self.__class__.__name__}(queue_wrapper={self.queue_wrapper!r})"

    def add_log_cmd(self, print_str: str):
        self.queue_wrapper.queue.append(LogQueueEntry(print_str))

    def add_pus_tc(self, pus_tc: PusTelecommand):
        self.queue_wrapper.queue.append(PusTcEntry(pus_tc))

    def add_ccsds_tc(self, space_packet: SpacePacket):
        self.queue_wrapper.queue.append(SpacePacketEntry(space_packet))

    def add_raw_tc(self, tc: bytes):
        self.queue_wrapper.queue.append(RawTcEntry(tc))

    def add_wait(self, wait_time: timedelta):
        self.queue_wrapper.queue.append(WaitEntry(wait_time))

    def add_wait_ms(self, wait_ms: int):
        self.queue_wrapper.queue.append(WaitEntry.from_millis(wait_ms))

    def add_packet_delay(self, delay: timedelta):
        self.queue_wrapper.queue.append(PacketDelayEntry(delay))

    def add_packet_delay_ms(self, delay_ms: int):
        self.queue_wrapper.queue.append(PacketDelayEntry.from_millis(delay_ms))
