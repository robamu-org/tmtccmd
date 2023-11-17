from __future__ import annotations
import enum
import logging
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from spacepackets.ecss import PusTelecommand, PusTelemetry
from tmtccmd.logging import LOG_DIR
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from logging import FileHandler

RAW_PUS_LOGGER_NAME = "tmtccmd_raw_pus_log"
RAW_PUS_FILE_BASE_NAME = "_".join(RAW_PUS_LOGGER_NAME.split("_")[:-1])

TMTC_LOGGER_NAME = "tmtccmd_file_log"
TMTC_FILE_BASE_NAME = "_".join(TMTC_LOGGER_NAME.split("_")[:-1])

__TMTC_LOGGER: Optional[logging.Logger] = None
__RAW_PUS_LOGGER: Optional[logging.Logger] = None


def date_suffix() -> str:
    return f"{datetime.now().date()}"


class TimedLogWhen(enum.Enum):
    PER_HOUR = "h"
    PER_MINUTE = "M"
    PER_SECOND = "S"
    PER_DAY = "D"


class RawTmtcLogBase:
    def __init__(
        self, logger: logging.Logger, log_repr: bool = True, log_raw_repr: bool = True
    ):
        self.logger = logger
        self.do_log_repr = log_repr
        self.do_log_raw_repr = log_raw_repr
        self.counter = 0

    def log_tc(self, packet: PusTelecommand):
        """Default log function which logs the Python packet representation and raw bytes"""
        prefix = self.tc_prefix(packet, self.counter)
        if self.do_log_repr:
            self.log_repr(prefix, packet)
        raw_bytes = packet.pack()
        self.__log_raw_inc_counter(prefix, raw_bytes)

    def log_tm(self, packet: PusTelemetry):
        """Default log function which logs the Python packet representation and raw bytes"""
        prefix = self.tm_prefix(packet, self.counter)
        if self.do_log_repr:
            self.log_repr(prefix, packet)
        raw_bytes = packet.pack()
        self.__log_raw_inc_counter(prefix, raw_bytes)

    def __log_raw_inc_counter(self, prefix: str, raw: bytes):
        self.log_bytes_readable(prefix, raw)
        if self.do_log_raw_repr:
            self.log_bytes_repr(prefix, raw)
        self.counter += 1

    def log_repr(self, prefix: str, packet: Union[PusTelecommand, PusTelemetry]):
        self.logger.info(f"{prefix} repr: {packet!r}")

    @staticmethod
    def tc_prefix(packet: PusTelecommand, counter: int):
        return f"tc {counter} [{packet.service}, {packet.subservice}]"

    @staticmethod
    def tm_prefix(packet: PusTelemetry, counter: int):
        return f"tm {counter} [{packet.service}, {packet.subservice}]"

    def log_bytes_readable(self, prefix: str, packet: bytes):
        self.logger.info(f"{prefix} raw readable hex: [{packet.hex(sep=',')}]")

    def log_bytes_repr(self, prefix: str, packet: bytes):
        self.logger.info(f"{prefix} raw repr: {packet!r}")


class RawTmtcTimedLogWrapper(RawTmtcLogBase):
    def __init__(
        self,
        when: TimedLogWhen,
        interval: int,
        logger: Optional[logging.Logger] = None,
        file_name: Path = Path(f"{LOG_DIR}/{RAW_PUS_FILE_BASE_NAME}"),
        suffix: Optional[str] = f"{date_suffix()}.log",
    ):
        """Create a raw TMTC timed rotating log wrapper.
        See the official Python documentation at
        https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler for
        more information on the input parameters

        :param when: A new log file will be created at the product of when and interval
        :param interval: A new log file will be created at the product of when and interval.
            For example, using when="H" and interval=3, a new log file will be created in three
            hour intervals
        :param file_name: Base filename of the log file
        """
        if logger is None:
            logger = logging.getLogger(RAW_PUS_LOGGER_NAME)
            logger.propagate = False
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        if suffix:
            file_name = f"{file_name}_{suffix}"
        handler = TimedRotatingFileHandler(
            filename=file_name, when=when.value, interval=interval
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        self.file_name = handler.baseFilename
        super().__init__(logger)


class RawTmtcRotatingLogWrapper(RawTmtcLogBase):
    def __init__(
        self,
        max_bytes: int,
        backup_count: int,
        logger: Optional[logging.Logger] = None,
        file_name: Path = Path(f"{LOG_DIR}/{RAW_PUS_FILE_BASE_NAME}"),
        suffix: Optional[str] = f"{date_suffix()}.log",
    ):
        """Create a raw TMTC rotating log wrapper.
        See the official Python documentation at
        https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler for
        more information on the input parameters

        :param max_bytes: Maximum number of bytes per file. If backup_count is non-zero, the handler
            will create a new file up to the number of back_up count files. If the maximum backup
            count is reached, the oldest files will be deleted
        :param backup_count: If this is zero, Only max_bytes can be stored. Otherwise, a rollover
            will occur when a file reaches max_bytes and up to back_count files can be created
            this way.
        :param file_name: Base filename of the log file
        :param suffix: Suffix of the log file. Can be used to change the used log file. The default
            argument will use a date suffix, which will lead to a new unique rotating log created
            every day
        """
        if logger is None:
            logger = logging.getLogger(RAW_PUS_LOGGER_NAME)
            # We don't want any loggers up the hierarchy to receive the logs, only the file
            logger.propagate = False
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        if suffix:
            file_name = f"{file_name}_{suffix}"
        handler = RotatingFileHandler(
            filename=file_name,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        self.file_name = handler.baseFilename
        super().__init__(logger)


class RegularTmtcLogWrapper:
    def __init__(
        self, file_name: Optional[Path] = None, logger: Optional[logging.Logger] = None
    ):
        if logger is None:
            logger = logging.getLogger(TMTC_LOGGER_NAME)
            logger.propagate = False
        log_dir = Path(LOG_DIR)
        if not log_dir.exists():
            log_dir.mkdir()
        if file_name is None:
            self.file_name = self.get_current_tmtc_file_name()
        else:
            self.file_name = file_name
        self.logger = logger
        self.file_handler = FileHandler(self.file_name)
        formatter = logging.Formatter()
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)
        self.logger.setLevel(logging.INFO)

    @classmethod
    def get_current_tmtc_file_name(cls) -> Path:
        return Path(
            f"{LOG_DIR}/{TMTC_FILE_BASE_NAME}_{datetime.now().date()}_"
            f"{datetime.now().time().strftime('%H%M%S')}.log"
        )

    def __del__(self):
        self.logger.removeHandler(self.file_handler)
        self.file_handler.close()
