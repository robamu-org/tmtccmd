import enum
from abc import abstractmethod


class Request(enum.IntEnum):
    NONE = 0
    TERMINATION_NO_ERROR = 1
    DELAY_IDLE = 2
    DELAY_LISTENER = 3


class BackendState:
    def __init__(self, req: Request):
        self.req = req
        self.mode_changed = False


class TcMode(enum.IntEnum):
    IDLE = (0,)
    ONE_QUEUE = (1,)
    MULTI_QUEUE = 2


class TmMode(enum.IntEnum):
    IDLE = 0
    LISTENER = 1


class BackendModeWrapper:
    def __init__(self):
        self.tc_mode = TcMode.IDLE
        self.tm_mode = TmMode.IDLE


class BackendState:
    def __init__(self):
        self.mode_wrapper = BackendModeWrapper()
        self.result = BackendState(Request.NONE)


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
