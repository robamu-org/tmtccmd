"""
@brief      This module is used to set up the global loggers
"""
from tmtccmd.version import get_version
import logging
import os
import sys
from datetime import datetime

import deprecation
from colorlog import ColoredFormatter


LOG_DIR = "log"
ERROR_LOG_FILE_NAME = "tmtc_error.log"


def add_colorlog_console_logger(logger: logging.Logger, log_level: int = logging.INFO):
    """This function can be used to apply the default library console logging output format to
    a custom logger.
    """
    from colorlog import StreamHandler

    dbg_fmt = (
        "%(log_color)s%(levelname)-8s %(cyan)s%(asctime)s.%(msecs)03d "
        "[%(name)s:%(lineno)d] %(reset)s%(message)s"
    )
    custom_formatter = CustomTmtccmdFormatter(
        info_fmt="%(log_color)s%(levelname)-8s %(cyan)s%(asctime)s."
        "%(msecs)03d %(reset)s%(message)s",
        dbg_fmt=dbg_fmt,
        err_fmt=dbg_fmt,
        warn_fmt=dbg_fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(custom_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(log_level)


def add_error_file_logger(logger: logging.Logger):
    file_format = logging.Formatter(
        fmt="%(levelname)-8s: %(asctime)s.%(msecs)03d [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # TODO: Use path relative to script dir, otherwise this craps everything
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
    error_file_handler = logging.FileHandler(
        filename=f"{LOG_DIR}/{ERROR_LOG_FILE_NAME}", encoding="utf-8", mode="w"
    )
    error_file_handler.setLevel(level=logging.WARNING)
    error_file_handler.setFormatter(file_format)
    logger.addHandler(error_file_handler)


@deprecation.deprecated(
    deprecated_in="v4.0.0a4",
    current_version=get_version(),
    details="Use a custom application logger or tmtccmd.get_lib_logger instead.",
)
def get_console_logger() -> logging.Logger:
    return logging.getLogger(__name__)


def __setup_tmtc_console_logger(
    root_logger: logging.Logger, propagate: bool, log_level: int
):
    """Set up the tmtccmd root logger.

    :return:    Returns the instance of the global logger
    """
    # Use colorlog for now because it allows more flexibility and custom messages
    # for different levels
    add_colorlog_console_logger(logger=root_logger)
    root_logger.setLevel(level=log_level)
    root_logger.propagate = propagate


def __set_up_coloredlogs_logger(logger: logging.Logger):
    try:
        import coloredlogs

        coloredlogs.install(
            level="INFO",
            logger=logger,
            milliseconds=True,
            fmt="%(asctime)s.%(msecs)03d %(hostname)s %(name)s[%(process)d] "
            "%(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except ImportError:
        print("Please install coloredlogs package first")


# Custom formatter. Allows different strings for info, error and debug output
class CustomTmtccmdFormatter(ColoredFormatter):
    def __init__(
        self, info_fmt: str, dbg_fmt: str, err_fmt: str, warn_fmt: str, datefmt=None
    ):
        self.err_fmt = err_fmt
        self.info_fmt = info_fmt
        self.dbg_fmt = dbg_fmt
        self.warn_fmt = warn_fmt
        super().__init__(fmt="%(levelno)d: %(msg)s", datefmt=datefmt, style="%")

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            self._style._fmt = self.dbg_fmt

        elif record.levelno == logging.INFO:
            self._style._fmt = self.info_fmt

        elif record.levelno == logging.ERROR:
            self._style._fmt = self.err_fmt

        elif record.levelno == logging.WARNING:
            self._style._fmt = self.warn_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result


def build_log_file_name(base_name: str):
    return f"{LOG_DIR}/{base_name}"


def get_current_time_string(ms_prec: bool) -> str:
    base_fmt = "%Y-%m-%d %H:%M:%S"
    if ms_prec:
        base_fmt += ".%f"
        return datetime.now().strftime(base_fmt)[:-3]
    return datetime.now().strftime(base_fmt)
