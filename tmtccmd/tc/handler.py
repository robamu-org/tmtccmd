from abc import abstractmethod, ABC

from tmtccmd.com_if import ComInterface
from tmtccmd.tc import TcQueueEntryBase, TcProcedureBase
from tmtccmd.tc.queue import QueueHelper, QueueWrapper, QueueEntryHelper


class FeedWrapper:
    def __init__(self, queue_wrapper: QueueWrapper, auto_dispatch: bool):
        from tmtccmd.core import ModeWrapper

        self.queue_helper = QueueHelper(queue_wrapper)
        self.dispatch_next_queue = auto_dispatch
        self.pause = False
        self.modes = ModeWrapper()


class TcHandlerBase(ABC):
    """Generic abstraction for a TC handler object. This object then takes care of sending
    packets by providing a send callback. It also provides telecommand queues by providing
    a queue fedder callback.
    """

    def __init__(self):
        pass

    @abstractmethod
    def send_cb(self, tc_queue_entry: QueueEntryHelper, com_if: ComInterface):
        """This function callback will be called for each queue entry. This also includes
        miscellaneous queue entries, for example the ones used to log additional information.
        It is up to the user code implementation to determine the concrete queue entry.

        In general, an implementation will perform the following steps:

        1. Determine the concrete queue entry. The
           :py:class:`tmtccmd.tc.PacketCastWrapper` helper class can be used to do this
        2. If applicable, retrieve the raw data to send from the queue entry and send it using
           the generic communication interface

        :param tc_queue_entry: Queue entry base type. The user can cast this back to the concrete
            type or just use duck typing if the concrete type is known
        :param com_if: Communication interface. Will generally be used to send the packet,
            using the py:meth:`tmtccmd.com_if.ComInterface.send` method
        """
        pass

    @abstractmethod
    def queue_finished_cb(self, info: TcProcedureBase):
        pass

    @abstractmethod
    def feed_cb(self, info: TcProcedureBase, wrapper: FeedWrapper):
        """This function will be called to retrieve a telecommand queue from the user code, based
        on a procedure. The passed feed wrapper can be used to set the TC queue or other
        parameter like the inter packet delay.

        :param info: Generic base class for a procedure. For example, the
            py:class:`tmtccmd.tc.DefaultProcedureInfo` class uses a service string
            and op code string which can be used in the user code to select between different
            telecommand queues being packed
        :param wrapper: Wrapper type around the queue. It also contains a queue helper class
            to simplify adding entries to the telecommand queue
        :return:
        """
        pass
