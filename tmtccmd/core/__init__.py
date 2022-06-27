from abc import abstractmethod
import enum

from tmtccmd.tc.ccsds_seq_sender import SeqResultWrapper, SenderMode


class TcMode(enum.IntEnum):
    IDLE = 0
    ONE_QUEUE = 1
    MULTI_QUEUE = 2


class TmMode(enum.IntEnum):
    IDLE = 0
    LISTENER = 1


class ModeWrapper:
    def __init__(self):
        self.tc_mode = TcMode.IDLE
        self.tm_mode = TmMode.IDLE

    def __str__(self):
        return f"{self.__class__.__name__}: tc_mode={self.tc_mode!r}, tm_mode={self.tm_mode!r}"


class BackendRequest(enum.IntEnum):
    NONE = 0
    TERMINATION_NO_ERROR = 1
    DELAY_IDLE = 2
    DELAY_LISTENER = 3
    DELAY_CUSTOM = 4
    CALL_NEXT = 5


class BackendState:
    def __init__(
        self,
        mode_wrapper: ModeWrapper = ModeWrapper(),
        req: BackendRequest = BackendRequest.NONE,
    ):
        self._mode_wrapper = mode_wrapper
        self._req = req
        self._recommended_delay = 0
        self._sender_res = SeqResultWrapper(SenderMode.DONE)

    @property
    def next_delay(self):
        return self._recommended_delay

    @property
    def request(self):
        return self._req

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
    def open_com_if(self):
        """Start the backend. Raise RuntimeError on failure"""
        pass

    @abstractmethod
    def close_com_if(self):
        pass

    @abstractmethod
    def periodic_op(self, ctrl: BackendController) -> BackendState:
        pass
