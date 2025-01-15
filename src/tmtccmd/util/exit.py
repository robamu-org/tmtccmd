import logging
import signal

from tmtccmd.core import BackendBase


def keyboard_interrupt_handler(tmtc_backend: BackendBase):
    tmtc_backend.close_com_if()
    logging.getLogger(__name__).info("Closing TMTC client")


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self):
        self.kill_now = True
        print("I was killed")
