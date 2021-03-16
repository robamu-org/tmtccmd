"""
@brief      This module is used to set up the global loggers
"""
import logging
import os
import sys


TMTC_LOGGER_NAME = "TMTC Logger"
ERROR_LOG_FILE_NAME = "tmtc_error.log"


# pylint: disable=arguments-differ
# pylint: disable=too-few-public-methods
class InfoFilter(logging.Filter):
    """
    Filter object, which is used so that only INFO and DEBUG messages are printed to stdout.
    """
    def filter(self, rec):
        if rec.levelno == logging.INFO:
            return rec.levelno
        return None


class DebugFilter(logging.Filter):
    """
    Filter object, which is used so that only INFO and DEBUG messages are printed to stdout.
    """
    def filter(self, rec):
        if rec.levelno == logging.DEBUG:
            return rec.levelno
        return None


def set_tmtc_logger() -> logging.Logger:
    """
    Sets the LOGGER object which will be used globally.
    """
    logger = logging.getLogger(TMTC_LOGGER_NAME)
    logger.setLevel(level=logging.DEBUG)
    generic_format = logging.Formatter(
        fmt='%(levelname)-8s: %(asctime)s.%(msecs)03d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    fault_format = logging.Formatter(
        fmt='%(levelname)-8s: %(asctime)s.%(msecs)03d | [%(filename)s:%(lineno)d] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    console_info_handler = logging.StreamHandler(stream=sys.stdout)
    console_info_handler.setLevel(logging.INFO)
    console_info_handler.addFilter(InfoFilter())

    console_debug_handler = logging.StreamHandler(stream=sys.stdout)
    console_debug_handler.setLevel(logging.DEBUG)
    console_debug_handler.addFilter(DebugFilter())

    console_error_handler = logging.StreamHandler(stream=sys.stderr)
    console_error_handler.setLevel(logging.WARNING)
    try:
        error_file_handler = logging.FileHandler(
            filename="log/" + ERROR_LOG_FILE_NAME, encoding='utf-8', mode='w')
    except FileNotFoundError:
        os.mkdir("log")
        error_file_handler = logging.FileHandler(
            filename="log/" + ERROR_LOG_FILE_NAME, encoding='utf-8', mode='w')

    error_file_handler.setLevel(level=logging.WARNING)

    error_file_handler.setFormatter(generic_format)
    console_info_handler.setFormatter(generic_format)
    console_debug_handler.setFormatter(fault_format)
    console_error_handler.setFormatter(fault_format)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_info_handler)
    logger.addHandler(console_debug_handler)
    logger.addHandler(console_error_handler)
    return logger


def get_logger() -> logging.Logger:
    """
    Get the global LOGGER instance.
    """
    logger = logging.getLogger(TMTC_LOGGER_NAME)
    return logger
