import signal
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


def keyboard_interrupt_handler(tmtc_backend: CcsdsTmtcBackend):
    tmtc_backend.close_listener()
    LOGGER.info("Closing TMTC client")


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self):
        self.kill_now = True
        print("I was killed")
