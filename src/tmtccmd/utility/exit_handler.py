import signal
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


def keyboard_interrupt_handler(tmtc_backend: TmTcHandler, com_interface: CommunicationInterface):
    tmtc_backend.close_listener(join=True, join_timeout_seconds=1.0)
    LOGGER.info("Closing TMTC client")


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self):
        self.kill_now = True
        print("I was killed")
