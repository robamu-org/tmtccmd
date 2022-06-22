from typing import Optional

from spacepackets.ccsds.spacepacket import SpacePacket
from spacepackets.ecss import PusTelecommand
from tmtccmd.tc.definitions import (
    QueueDequeT,
    LogQueueEntry,
    PusTcEntry,
    RawTcEntry,
    WaitEntry,
)


class QueueWrapper:
    def __init__(self, queue: Optional[QueueDequeT], inter_cmd_delay: bool = True):
        self.queue = queue
        self.inter_cmd_delay = inter_cmd_delay


class QueueHelper:
    def __init__(self, queue_wrapper: QueueWrapper):
        self.queue_wrapper = queue_wrapper

    def add_log_cmd(self, print_str: str):
        self.queue_wrapper.queue.appendleft(LogQueueEntry(print_str))

    def add_pus_tc(self, pus_tc: PusTelecommand):
        self.queue_wrapper.queue.appendleft(PusTcEntry(pus_tc))

    def add_ccsds_tc(self, space_packet: SpacePacket):
        pass

    def add_raw_tc(self, tc: bytes):
        self.queue_wrapper.queue.appendleft(RawTcEntry(tc))

    def add_wait(self, wait_secs: float):
        self.queue_wrapper.queue.appendleft(WaitEntry(wait_secs))
