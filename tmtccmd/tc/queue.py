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
        inter_cmd_delay: float = 0.0,
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
        self.queue_wrapper.queue.appendleft(LogQueueEntry(print_str))

    def add_pus_tc(self, pus_tc: PusTelecommand):
        self.queue_wrapper.queue.appendleft(PusTcEntry(pus_tc))

    def add_ccsds_tc(self, space_packet: SpacePacket):
        self.queue_wrapper.queue.appendleft(SpacePacketEntry(space_packet))

    def add_raw_tc(self, tc: bytes):
        self.queue_wrapper.queue.appendleft(RawTcEntry(tc))

    def add_wait(self, wait_secs: float):
        self.queue_wrapper.queue.appendleft(WaitEntry(wait_secs))

    def add_packet_delay(self, delay: float):
        self.queue_wrapper.queue.appendleft(PacketDelayEntry(delay))
