from abc import abstractmethod

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.core.backend import ProcedureInfo
from tmtccmd.tc.definitions import TcQueueT, TcQueueEntryBase


class TcHandlerBase:
    def __init__(self):
        pass

    @abstractmethod
    def pre_send_cb(
        self, tc_queue_entry: TcQueueEntryBase, com_if: CommunicationInterface
    ):
        pass

    @abstractmethod
    def pass_queue(self, info: ProcedureInfo) -> TcQueueT:
        pass

    @abstractmethod
    def queue_finished_cb(self, service: str, op_code: str):
        pass

    def feed_cb(self):
        pass
