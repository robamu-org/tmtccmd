from abc import abstractmethod

from typing import Union, Any

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.config import QueueCommands
from tmtccmd.config.definitions import TcQueueEntryArg


class TcHandlerBase:
    def __init__(self):
        pass

    @abstractmethod
    def send_callback(
        self,
        tc_queue_entry: Union[bytes, QueueCommands],
        com_if: CommunicationInterface,
        queue_entry_arg: TcQueueEntryArg,
        user_arg: Any,
    ):
        pass
