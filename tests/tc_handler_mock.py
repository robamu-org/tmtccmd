from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.tc.definitions import TcQueueEntryBase, TcProcedureBase
from tmtccmd.tc.handler import TcHandlerBase, FeedWrapper


class TcHandler(TcHandlerBase):
    def send_cb(self, tc_queue_entry: TcQueueEntryBase, com_if: CommunicationInterface):
        pass

    def queue_finished_cb(self, info: TcProcedureBase):
        pass

    def feed_cb(self, info: TcProcedureBase, wrapper: FeedWrapper):
        pass
