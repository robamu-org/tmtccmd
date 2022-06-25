from abc import abstractmethod
from typing import Optional

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.core.modes import ModeWrapper
from tmtccmd.tc.definitions import TcQueueEntryBase, ProcedureInfo
from tmtccmd.tc.queue import QueueHelper, QueueWrapper


class FeedWrapper:
    def __init__(self, queue_wrapper: QueueWrapper, auto_dispatch: bool):
        self.queue_helper = QueueHelper(queue_wrapper)
        self.dispatch_next_queue = auto_dispatch
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
