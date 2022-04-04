import logging
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

FILE_BASE_NAME = "pus-log"
LOGGER_NAME = "tmtccmd.pus-log"
__PUS_LOGGER: Optional[logging.Logger] = None


def create_pus_file_logger() -> logging.Logger:
    """Create a logger to log raw PUS messages by returning a rotating file handler which has
    the current date in its log file name.
    :return:
    """
    global __PUS_LOGGER
    file_name = f"{FILE_BASE_NAME}_{datetime.now().date()}.txt"
    if __PUS_LOGGER is None:
        __PUS_LOGGER = logging.getLogger(LOGGER_NAME)
        handler = RotatingFileHandler(filename=file_name, maxBytes=4096, backupCount=10)
        formatter = logging.Formatter(
            fmt="(asctime)s.%(msecs)03d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt=formatter)
        __PUS_LOGGER.addHandler(handler)
    return __PUS_LOGGER


def log_pus_packet(packet: bytes):
    global __PUS_LOGGER
    if __PUS_LOGGER is None:
        return
    __PUS_LOGGER.info(f"hex [{packet.hex(sep=',')}]")
