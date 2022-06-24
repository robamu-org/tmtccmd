import enum


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
