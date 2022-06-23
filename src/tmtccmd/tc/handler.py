from abc import abstractmethod
from typing import Optional

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.core.ccsds_backend import ProcedureInfo
from tmtccmd.core.modes import ModeWrapper
from tmtccmd.tc.definitions import TcQueueEntryBase, QueueDequeT


class FeedWrapper:
    def __init__(self):
        self.current_queue: Optional[QueueDequeT] = None
        self.dispatch_next_queue = False
        self.pause = False
        self.modes = ModeWrapper()


class TcHandlerBase:
    def __init__(self):
        pass

    @abstractmethod
    def send_cb(self, tc_queue_entry: TcQueueEntryBase, com_if: CommunicationInterface):
        pass

    @abstractmethod
    def queue_finished_cb(self, info: ProcedureInfo):
        pass

    @abstractmethod
    def feed_cb(self, info: Optional[ProcedureInfo], wrapper: FeedWrapper):
        pass
