import enum
from abc import abstractmethod

from tmtccmd.core.modes import ModeWrapper, TcMode, TmMode
from tmtccmd.tc.ccsds_seq_sender import SeqResultWrapper, SenderMode


class Request(enum.IntEnum):
    NONE = 0
    TERMINATION_NO_ERROR = 1
    DELAY_IDLE = 2
    DELAY_LISTENER = 3


class BackendState:
    def __init__(
        self, mode_wrapper: ModeWrapper = ModeWrapper(), req: Request = Request.NONE
    ):
        self._mode_wrapper = mode_wrapper
        self._req = req
        self._sender_res = SeqResultWrapper(SenderMode.DONE)

    @property
    def request(self):
        return self._req

    @property
    def mode(self):
        return self._mode_wrapper.mode

    @property
    def sender_res(self):
        return self._sender_res

    @property
    def tc_mode(self):
        return self._mode_wrapper.tc_mode

    @property
    def tm_mode(self):
        return self._mode_wrapper.tm_mode

    @property
    def mode_wrapper(self):
        return self._mode_wrapper


class BackendController:
    def __init__(self):
        self.next_tc_mode = TcMode.IDLE
        self.next_tm_mode = TmMode.IDLE


class BackendBase:
    @abstractmethod
    def initialize(self):
        """Initialize the backend. Raise RuntimeError or ValueError on failure"""

    @abstractmethod
    def start_listener(self, perform_op_immediately: bool):
        """Start the backend. Raise RuntimeError on failure"""

    @abstractmethod
    def periodic_op(self, ctrl: BackendController) -> BackendState:
        pass
