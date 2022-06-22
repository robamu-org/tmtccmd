from abc import abstractmethod
from typing import Optional

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.core.backend import ProcedureInfo
from tmtccmd.tc.definitions import TcQueueEntryBase


class TcHandlerBase:
    def __init__(self):
        pass

    @abstractmethod
    def pre_send_cb(
        self, tc_queue_entry: TcQueueEntryBase, com_if: CommunicationInterface
    ):
        pass

    @abstractmethod
    def queue_finished_cb(self, info: ProcedureInfo):
        pass

    @abstractmethod
    def feed_cb(self, info: Optional[ProcedureInfo]):
        pass
