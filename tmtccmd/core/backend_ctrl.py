from tmtccmd.core import TcMode, TmMode


class BackendController:
    def __init__(self):
        self.next_tc_mode = TcMode.IDLE
        self.next_tm_mode = TmMode.IDLE
