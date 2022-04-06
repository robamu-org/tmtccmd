import logging
import os
from typing import Optional, Tuple
from datetime import datetime
from tmtccmd.logging import LOG_DIR
from spacepackets.ccsds.spacepacket import PacketTypes
from logging.handlers import RotatingFileHandler
from logging import FileHandler

RAW_PUS_FILE_BASE_NAME = "pus-log"
RAW_PUS_LOGGER_NAME = "pus-log"

TMTC_FILE_BASE_NAME = "tmtc-log"
TMTC_LOGGER_NAME = "tmtc-log"

__TMTC_LOGGER: Optional[logging.Logger] = None
__RAW_PUS_LOGGER: Optional[logging.Logger] = None


def create_raw_pus_file_logger(max_bytes: int = 8192 * 16) -> logging.Logger:
    """Create a logger to log raw PUS messages by returning a rotating file handler which has
    the current date in its log file name. This function is not thread-safe.
    :return:
    """
    global __RAW_PUS_LOGGER
    file_name = get_current_raw_file_name()
    if __RAW_PUS_LOGGER is None:
        __RAW_PUS_LOGGER = logging.getLogger(RAW_PUS_LOGGER_NAME)
        handler = RotatingFileHandler(
            filename=file_name, maxBytes=max_bytes, backupCount=10
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt=formatter)
        __RAW_PUS_LOGGER.addHandler(handler)
        __RAW_PUS_LOGGER.setLevel(logging.INFO)
    __RAW_PUS_LOGGER.info(
        f"tmtccmd started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return __RAW_PUS_LOGGER


def get_current_raw_file_name() -> str:
    return f"{LOG_DIR}/{RAW_PUS_FILE_BASE_NAME}_{datetime.now().date()}.log"


def get_current_tmtc_file_name() -> str:
    return (
        f"{LOG_DIR}/{TMTC_FILE_BASE_NAME}_{datetime.now().date()}_"
        f"{datetime.now().time().strftime('%H%M%S')}.log"
    )


def log_raw_pus_tc(packet: bytes, srv_subservice: Optional[Tuple[int, int]] = None):
    global __RAW_PUS_LOGGER
    if __RAW_PUS_LOGGER is None:
        __RAW_PUS_LOGGER = create_raw_pus_file_logger()
    type_str = "TC"
    if srv_subservice is not None:
        type_str += f" [{srv_subservice[0], srv_subservice[1]}"

    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __RAW_PUS_LOGGER.info(logged_msg)


def log_raw_pus_tm(packet: bytes, srv_subservice: Optional[Tuple[int, int]] = None):
    global __RAW_PUS_LOGGER
    if __RAW_PUS_LOGGER is None:
        __RAW_PUS_LOGGER = create_raw_pus_file_logger()
    type_str = "TM"
    if srv_subservice is not None:
        type_str += f" [{srv_subservice[0], srv_subservice[1]}"

    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __RAW_PUS_LOGGER.info(logged_msg)


def log_raw_unknown_packet(packet: bytes, packet_type: PacketTypes):
    global __RAW_PUS_LOGGER
    if __RAW_PUS_LOGGER is None:
        __RAW_PUS_LOGGER = create_raw_pus_file_logger()
    if packet_type == PacketTypes.TC:
        type_str = "Unknown TC Packet"
    else:
        type_str = "Unknown TM Packet"
    logged_msg = f"{type_str} | hex [{packet.hex(sep=',')}]"
    __RAW_PUS_LOGGER.info(logged_msg)


def create_tmtc_logger():
    """Create a generic TMTC logger which logs both to a unique file for a TMTC session.
    This functions is not thread-safe.
    :return:
    """
    global __TMTC_LOGGER
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
    # This should create a unique event log file for most cases. If for some reason this is called
    # with the same name, the events will appended to an old file which was created in the same
    # second. This is okay.
    file_name = get_current_tmtc_file_name()
    if __TMTC_LOGGER is None:
        __TMTC_LOGGER = logging.getLogger(TMTC_LOGGER_NAME)
        file_handler = FileHandler(filename=file_name)
        formatter = logging.Formatter()
        file_handler.setFormatter(fmt=formatter)
        __TMTC_LOGGER.addHandler(file_handler)
        __TMTC_LOGGER.setLevel(logging.INFO)
    return __TMTC_LOGGER


def get_tmtc_file_logger() -> logging.Logger:
    """Returns a generic TMTC logger which logs both to a unique file for a TMTC session.
    This functions is not thread-safe.
    :return:
    """
    global __TMTC_LOGGER
    if __TMTC_LOGGER is None:
        __TMTC_LOGGER = create_tmtc_logger()
    return __TMTC_LOGGER
