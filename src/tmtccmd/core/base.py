import enum
from abc import abstractmethod


class Request(enum.IntEnum):
    NONE = 0
    TERMINATION_NO_ERROR = 1
    DELAY_IDLE = 2
    DELAY_LISTENER = 3


class BackendResult:
    def __init__(self, req: Request):
        self.req = req
        self.mode_changed = False


class BackendBase:
    @abstractmethod
    def initialize(self):
        """Initialize the backend. Raise RuntimeError or ValueError on failure"""

    @abstractmethod
    def start_listener(self, perform_op_immediately: bool):
        """Start the backend. Raise RuntimeError on failure"""

    @abstractmethod
    def periodic_op(self) -> BackendResult:
        pass
