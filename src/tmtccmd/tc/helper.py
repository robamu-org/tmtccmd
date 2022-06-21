from spacepackets.ecss import PusTelecommand
from tmtccmd.tc.definitions import (
    TcQueueT,
    LogQueueEntry,
    PusTcEntry,
    RawTcEntry,
    WaitEntry,
)


class QueueWrapper:
    def __init__(self, queue: TcQueueT):
        self.queue = queue

    def add_log_cmd(self, print_str: str):
        self.queue.appendleft(LogQueueEntry(print_str))

    def add_pus_tc(self, pus_tc: PusTelecommand):
        self.queue.appendleft(PusTcEntry(pus_tc))

    def add_raw_tc(self, tc: bytes):
        self.queue.appendleft(RawTcEntry(tc))

    def add_wait(self, wait_secs: float):
        self.queue.appendleft(WaitEntry(wait_secs))
