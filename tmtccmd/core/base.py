import enum
from abc import abstractmethod


class FrontendBase:
    @abstractmethod
    def start(self, args: any):
        """
        Start the frontend.
        :return:
        """


class TcMode(enum.IntEnum):
    IDLE = 0
    ONE_QUEUE = 1
    MULTI_QUEUE = 2


class TmMode(enum.IntEnum):
    IDLE = 0
    LISTENER = 1


class BackendRequest(enum.IntEnum):
    """These requests can be treated like recommendations on what to do after calling the backend
    handler functions and the :py:meth:`BackendState.mode_to_req` function.

    Brief explanation of fields:
     1. NONE: No special recommendation
     2. TERMINATION_NO_ERROR: Will be returned for the One Queue mode after finishing queue
        handling.
     3. DELAY_IDLE: TC and TM mode are idle, so there is nothing to do
     4. DELAY_LISTENER: TC handling is not active but TM listening is active. Delay to
        wait for new TM packets
     5. CALL_NEXT: It is recommended to call the handler functions immediately, for example to
        handle the next entry in the TC queue
    """

    NONE = 0
    TERMINATION_NO_ERROR = 1
    DELAY_IDLE = 2
    DELAY_LISTENER = 3
    DELAY_CUSTOM = 4
    CALL_NEXT = 5


class ModeWrapper:
    def __init__(self):
        self.tc_mode = TcMode.IDLE
        self.tm_mode = TmMode.IDLE

    def __str__(self):
        return f"{self.__class__.__name__}: tc_mode={self.tc_mode!r}, tm_mode={self.tm_mode!r}"
