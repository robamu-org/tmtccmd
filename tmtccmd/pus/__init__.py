"""This module contains PUS data structures and helpers common for both PUS telemetry and
telecommands.

Content:

* :py:class:`tmtccmd.pus.VerificationWrapper` helper class
* Re-export of the most important PUS service specific data structures from their respective
  :py:mod:`tmtccmd.tc` and :py:mod:`tmtccmd.tm` module.
"""
from enum import IntEnum
from typing import Optional

from .s11_tc_sched import Subservice as Pus11Subservices
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import RequestId
import spacepackets.ecss.pus_1_verification as pus_1
from spacepackets.ecss.pus_verificator import (
    VerificationStatus,
    StatusField,
    PusVerificator,
    TmCheckResult,
)
import logging

from tmtccmd.util.conf_util import AnsiColors


class CustomFsfwPusService(IntEnum):
    SERVICE_200_MODE = 200


class VerificationWrapper:
    def __init__(
        self,
        pus_verificator: PusVerificator,
        console_logger: Optional[logging.Logger],
        file_logger: Optional[logging.Logger],
    ):
        self.pus_verificator = pus_verificator
        self.console_logger = console_logger
        self.file_logger = file_logger
        self.with_colors = True

    @property
    def verificator(self) -> PusVerificator:
        return self.pus_verificator

    def dlog(self, log_str: str, level: int = logging.INFO):
        if self.console_logger is not None:
            self.console_logger.log(level, log_str)
        elif self.file_logger is not None:
            self.file_logger.info(level, log_str)

    def add_tc(self, pus_tc: PusTelecommand) -> bool:
        return self.pus_verificator.add_tc(pus_tc)

    def add_tm(self, srv_1_tm: pus_1.Service1Tm) -> TmCheckResult:
        return self.pus_verificator.add_tm(srv_1_tm)

    def log_to_console(self, srv_1_tm: pus_1.Service1Tm, res: TmCheckResult):
        self.log_to_console_from_req_id(
            srv_1_tm.tc_req_id, res, pus_1.Subservice(srv_1_tm.subservice)
        )

    def log_to_console_from_req_id(
        self,
        req_id: RequestId,
        res: TmCheckResult,
        subservice: Optional[pus_1.Subservice] = None,
    ):
        return self.log_progress_to_console_from_status(res.status, req_id, subservice)

    def log_to_file(self, srv_1_tm: pus_1.Service1Tm, res: TmCheckResult):
        self.log_to_file_from_req_id(
            srv_1_tm.tc_req_id, res, pus_1.Subservice(srv_1_tm.subservice)
        )

    def log_to_file_from_req_id(
        self,
        req_id: RequestId,
        res: TmCheckResult,
        subservice: Optional[pus_1.Subservice] = None,
    ):
        self.log_to_file_from_status(res.status, req_id, subservice)

    def log_to_file_from_status(
        self,
        status: VerificationStatus,
        req_id: RequestId,
        subservice: Optional[pus_1.Subservice] = None,
    ):
        if self.file_logger is None:
            raise ValueError("No valid file logger was set")
        acc_char = gen_file_char_from_status(status.accepted)
        start_char = gen_file_char_from_status(status.started)
        step_char = gen_file_char_from_status(status.step)
        fin_char = gen_file_char_from_status(status.completed)
        step_num = self.step_num(status)
        first_str = self._get_info_string(subservice)
        second_str = f"Request ID {req_id.as_u32():#04x}"
        completion_str = ""
        if status.completed == StatusField.SUCCESS:
            completion_str = " S"
        third_str = (
            f"acc ({acc_char}) sta ({start_char}) ste ({step_char}, {step_num}) "
            f"fin ({fin_char}){completion_str}"
        )

        self.file_logger.info(f"{first_str} | {second_str} | {third_str}")

    def log_progress_to_console_from_status(
        self,
        status: VerificationStatus,
        req_id: RequestId,
        subservice: Optional[pus_1.Subservice] = None,
    ):
        if self.console_logger is None:
            raise ValueError("Invalid console logger")
        acc_char = gen_console_char_from_status(status.accepted, self.with_colors)
        start_char = gen_console_char_from_status(status.started, self.with_colors)
        step_char = gen_console_char_from_status(status.step, self.with_colors)
        fin_char = gen_console_char_from_status(status.completed, self.with_colors)
        step_num = self.step_num(status)
        first_str = self._get_info_string(subservice)
        second_str = f"Request ID {req_id.as_u32():#04x}"
        completion_str = ""
        if status.completed == StatusField.SUCCESS:
            completion_str = f" {AnsiColors.BOLD}{AnsiColors.YELLOW}\u2728"
        third_str = (
            f"acc ({acc_char}) sta ({start_char}) ste ({step_char}, {step_num}) "
            f"fin ({fin_char}){completion_str}"
        )
        self.console_logger.info(f"{first_str} | {second_str} | {third_str}")

    @staticmethod
    def step_num(status: VerificationStatus):
        if not status.step_list:
            return "0"
        else:
            return f"{max(status.step_list)}"

    @staticmethod
    def _get_info_string(subservice: pus_1.Subservice):
        status_str = "Status"
        if subservice is not None:
            if subservice == pus_1.Subservice.TM_ACCEPTANCE_SUCCESS:
                status_str = "Acceptance success"
            elif subservice == pus_1.Subservice.TM_ACCEPTANCE_FAILURE:
                status_str = "Acceptance failure"
            elif subservice == pus_1.Subservice.TM_START_SUCCESS:
                status_str = "Start success"
            elif subservice == pus_1.Subservice.TM_START_FAILURE:
                status_str = "Start failure"
            elif subservice == pus_1.Subservice.TM_STEP_SUCCESS:
                status_str = "Step success"
            elif subservice == pus_1.Subservice.TM_STEP_FAILURE:
                status_str = "Step failure"
            elif subservice == pus_1.Subservice.TM_COMPLETION_SUCCESS:
                status_str = "Completion success"
            elif subservice == pus_1.Subservice.TM_COMPLETION_FAILURE:
                status_str = "Completion failure"
        return f"{status_str} of TC".ljust(25)


def gen_file_char_from_status(status: StatusField):
    if status == StatusField.UNSET:
        return "-"
    elif status == StatusField.FAILURE:
        return "F"
    elif status == StatusField.SUCCESS:
        return "S"


def gen_console_char_from_status(status: StatusField, with_color: bool):
    if status == StatusField.UNSET:
        return dash_unicode(with_color)
    elif status == StatusField.SUCCESS:
        return tick_mark_unicode(with_color)
    elif status == StatusField.FAILURE:
        return cross_mark_unicode(with_color)


def dash_unicode(with_color: bool) -> str:
    if with_color:
        return f"{AnsiColors.YELLOW}-{AnsiColors.RESET}"
    else:
        return "-"


def tick_mark_unicode(with_color: bool) -> str:
    if with_color:
        return f"{AnsiColors.GREEN}\u2713{AnsiColors.RESET}"
    else:
        return "\u2713"


def cross_mark_unicode(with_color: bool) -> str:
    if with_color:
        return f"{AnsiColors.RED}\u274c{AnsiColors.RESET}"
    else:
        return "\u274c"
