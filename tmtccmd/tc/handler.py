from abc import abstractmethod, ABC

from tmtccmd.com import ComInterface
from tmtccmd.tc.procedure import ProcedureWrapper
from tmtccmd.tc.queue import QueueWrapper, QueueEntryHelper


class FeedWrapper:
    """This class wraps the queue and some additional information and useful fields which
    can be set by the user.

    :var queue_helper: Can be used to simplify insertion of queue entries like telecommands into
        the queue
    :var dispatch_next_queue: Can be used to prevent the dispatch of the queue
    :var modes: Currently contains the current TC Mode and TM mode of the calling handler class
    """

    def __init__(self, queue_wrapper: QueueWrapper, auto_dispatch: bool):
        from tmtccmd.core.base import ModeWrapper

        self.queue_wrapper = queue_wrapper
        self.dispatch_next_queue = auto_dispatch
        self.modes = ModeWrapper()


class SendCbParams:
    """Wrapper for all important parameters passed to the TC send callback.

    :var info: Procedure info about the procedure this queue entry is related too
    :var entry: Queue entry base type. The user can cast this back to the concrete
            type or just use duck typing if the concrete type is known
    :var com_if: Communication interface. Will generally be used to send the packet,
            using the :py:func:`tmtccmd.com_if.ComInterface.send` method
    """

    def __init__(
        self, info: ProcedureWrapper, entry: QueueEntryHelper, com_if: ComInterface
    ):
        """Creates the parameters passed to the send callback."""
        self.info = info
        self.entry = entry
        self.com_if = com_if


class TcHandlerBase(ABC):
    """Generic abstract class for a TC handler object. Should be implemented by the user.
    This object then takes care of sending packets by providing the :py:meth:`send_cb`
    send-callback. It also provides telecommand queues by providing the :py:meth:`feed_cb` queue
    feeder callback.
    """

    def __init__(self):
        pass

    @abstractmethod
    def send_cb(self, send_params: SendCbParams):
        """This function callback will be called for each queue entry. This also includes
        miscellaneous queue entries, for example the ones used to log additional information.
        It is up to the user code implementation to determine the concrete queue entry and what
        to do with it.

        In general, an implementation will perform the following steps:

        1. Determine the queue entry and what to do with it
        2. If applicable, retrieve the raw data to send from the queue entry and send it using
           the generic communication interface

        All delay related entries will generally be handled by the send queue consumer so there
        is no need to manually delay the application in this callback. However, the queue consumer
        will not handle log entries so the user needs to take care of handling these
        entries and log the content to a console, file logger or any other system used to log
        something.

        :param send_params:
        """
        pass

    @abstractmethod
    def queue_finished_cb(self, info: ProcedureWrapper):
        pass

    @abstractmethod
    def feed_cb(self, info: ProcedureWrapper, wrapper: FeedWrapper):
        """This function will be called to retrieve a telecommand queue from the user code, based
        on a procedure. The passed feed wrapper can be used to set the TC queue or other
        parameter like the inter-packet delay.

        :param info: Generic base class for a procedure. For example, the
            py:class:`tmtccmd.tc.DefaultProcedureInfo` class uses a service string
            and op code string which can be used in the user code to select between different
            telecommand queues being packed
        :param wrapper: Wrapper type around the queue. It also contains a queue helper class
            to simplify adding entries to the telecommand queue
        :return:
        """
        pass
