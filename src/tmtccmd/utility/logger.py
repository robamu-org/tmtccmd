"""
@brief      This module is used to set up the global loggers
"""
import logging
import os
import sys


TMTC_LOGGER_NAME = "TMTC Console Logger"
TMTC_FILE_LOGGER_NAME = "TMTC File Logger"
ERROR_LOG_FILE_NAME = "tmtc_error.log"
__CONSOLE_LOGGER_SET_UP = False
__FILE_LOGER_SET_UP = False


# pylint: disable=arguments-differ
# pylint: disable=too-few-public-methods
class InfoFilter(logging.Filter):
    """Filter object, which is used so that only INFO and DEBUG messages are printed to stdout.
    """
    def filter(self, rec):
        if rec.levelno == logging.INFO:
            return rec.levelno
        return None


class DebugFilter(logging.Filter):
    """Filter object, which is used so that only DEBUG messages are printed to stdout.
    """
    def filter(self, rec):
        if rec.levelno == logging.DEBUG:
            return rec.levelno
        return None


def set_tmtc_console_logger() -> logging.Logger:
    """Sets the LOGGER object which will be used globally. This needs to be called before
    using the logger.
    :return:    Returns the instance of the global logger
    """
    global __CONSOLE_LOGGER_SET_UP
    logger = logging.getLogger(TMTC_LOGGER_NAME)
    logger.setLevel(level=logging.DEBUG)

    # Use colorlog for now because it allows more flexibility and custom messages
    # for different levels
    set_up_colorlog_logger(logger=logger)

    # set_up_coloredlogs_logger(logger=logger)

    file_format = logging.Formatter(
        fmt='%(levelname)-8s: %(asctime)s.%(msecs)03d | [%(filename)s:%(lineno)d] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_error_handler = logging.StreamHandler(stream=sys.stderr)
    console_error_handler.setLevel(logging.WARNING)

    try:
        error_file_handler = logging.FileHandler(
            filename=f"log/{ERROR_LOG_FILE_NAME}", encoding='utf-8', mode='w'
        )
    except FileNotFoundError:
        os.mkdir("log")
        error_file_handler = logging.FileHandler(
            filename=f"log/{ERROR_LOG_FILE_NAME}", encoding='utf-8', mode='w'
        )
    error_file_handler.setLevel(level=logging.WARNING)
    error_file_handler.setFormatter(file_format)
    logger.addHandler(error_file_handler)

    __CONSOLE_LOGGER_SET_UP = True
    return logger


def set_up_coloredlogs_logger(logger: logging.Logger):
    try:
        import coloredlogs
        coloredlogs.install(
            level='INFO', logger=logger, milliseconds=True,
            fmt='%(asctime)s.%(msecs)03d %(hostname)s %(name)s[%(process)d] %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    except ImportError:
        print("Please install coloredlogs package first")


def set_up_colorlog_logger(logger: logging.Logger):
    from colorlog import ColoredFormatter, StreamHandler
    generic_format = ColoredFormatter(
        fmt='%(log_color)s%(levelname)-8s %(cyan)s%(asctime)s.%(msecs)03d %(reset)s%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    fault_format = ColoredFormatter(
        fmt='%(log_color)s%(levelname)-8s %(cyan)s%(asctime)s.%(msecs)03d '
            '[%(filename)s:%(lineno)d] %(reset)s%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_format = logging.Formatter(
        fmt='%(levelname)-8s: %(asctime)s.%(msecs)03d [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_info_handler = StreamHandler(stream=sys.stdout)
    console_info_handler.setLevel(logging.INFO)
    console_info_handler.addFilter(InfoFilter())

    console_debug_handler = logging.StreamHandler(stream=sys.stdout)
    console_debug_handler.setLevel(logging.DEBUG)
    console_debug_handler.addFilter(DebugFilter())

    console_error_handler = logging.StreamHandler(stream=sys.stderr)
    console_error_handler.setLevel(logging.WARNING)

    try:
        error_file_handler = logging.FileHandler(
            filename=f"log/{ERROR_LOG_FILE_NAME}", encoding='utf-8', mode='w'
        )
    except FileNotFoundError:
        os.mkdir("log")
        error_file_handler = logging.FileHandler(
            filename=f"log/{ERROR_LOG_FILE_NAME}", encoding='utf-8', mode='w'
        )

    error_file_handler.setLevel(level=logging.WARNING)
    error_file_handler.setFormatter(file_format)
    console_info_handler.setFormatter(generic_format)
    console_debug_handler.setFormatter(fault_format)
    console_error_handler.setFormatter(fault_format)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_info_handler)
    logger.addHandler(console_debug_handler)
    logger.addHandler(console_error_handler)


def get_console_logger(set_up_logger: bool = False) -> logging.Logger:
    global __CONSOLE_LOGGER_SET_UP
    """Get the global console logger instance. Error logs will still be saved to an error file
    """
    logger = logging.getLogger(TMTC_LOGGER_NAME)
    if set_up_logger and not __CONSOLE_LOGGER_SET_UP:
        __CONSOLE_LOGGER_SET_UP = True
        set_tmtc_console_logger()
    return logger
