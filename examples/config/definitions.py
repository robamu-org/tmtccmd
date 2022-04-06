from spacepackets.ecss import PusTelecommand

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.logging import get_console_logger

APID = 0xEF
LOGGER = get_console_logger()


def pre_send_cb(
    data: bytes,
    com_if: CommunicationInterface,
    cmd_info: PusTelecommand,
    _user_args: any,
):
    LOGGER.info(cmd_info)
    com_if.send(data=data)
