import logging
from typing import Optional, Tuple
from datetime import datetime
from tmtccmd.logging import LOG_DIR
from spacepackets.ccsds.spacepacket import PacketTypes
from logging.handlers import RotatingFileHandler

FILE_BASE_NAME = "pus-log"
LOGGER_NAME = "pus-log"
__PUS_LOGGER: Optional[logging.Logger] = None


def create_pus_file_logger() -> logging.Logger:
    """Create a logger to log raw PUS messages by returning a rotating file handler which has
    the current date in its log file name.
    :return:
    """
    global __PUS_LOGGER
    file_name = get_current_file_name()
    if __PUS_LOGGER is None:
        __PUS_LOGGER = logging.getLogger(LOGGER_NAME)
        handler = RotatingFileHandler(
            filename=file_name, maxBytes=4096 * 4, backupCount=10
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt=formatter)
        __PUS_LOGGER.addHandler(handler)
        __PUS_LOGGER.setLevel(logging.INFO)
    __PUS_LOGGER.info(
        f"tmtccmd started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return __PUS_LOGGER


def get_current_file_name() -> str:
    return f"{LOG_DIR}/{FILE_BASE_NAME}_{datetime.now().date()}.log"


def log_pus_tc(packet: bytes, srv_subservice: Optional[Tuple[int, int]] = None):
    global __PUS_LOGGER
    if __PUS_LOGGER is None:
        __PUS_LOGGER = create_pus_file_logger()
    type_str = "TC"
    if srv_subservice is not None:
        type_str += f" [{srv_subservice[0], srv_subservice[1]}"

    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __PUS_LOGGER.info(logged_msg)


def log_pus_tm(packet: bytes, srv_subservice: Optional[Tuple[int, int]] = None):
    global __PUS_LOGGER
    if __PUS_LOGGER is None:
        __PUS_LOGGER = create_pus_file_logger()
    type_str = "TM"
    if srv_subservice is not None:
        type_str += f" [{srv_subservice[0], srv_subservice[1]}"

    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __PUS_LOGGER.info(logged_msg)


def log_unknown_packet(packet: bytes, packet_type: PacketTypes):
    global __PUS_LOGGER
    if __PUS_LOGGER is None:
        __PUS_LOGGER = create_pus_file_logger()
    if packet_type == PacketTypes.TC:
        type_str = "Unknown TC Packet"
    else:
        type_str = "Unknown TM Packet"
    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __PUS_LOGGER.info(logged_msg)
