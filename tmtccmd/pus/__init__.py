from enum import IntEnum
from typing import Optional

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.defs import PusServices
from spacepackets.ecss.pus_1_verification import RequestId
import spacepackets.ecss.pus_1_verification as pus_1
from spacepackets.ecss.pus_verificator import (
    VerificationStatus,
    StatusField,
    PusVerificator,
    TmCheckResult,
)
from .seqcnt import FileSeqCountProvider, ProvidesSeqCount
import logging

from tmtccmd.utility.conf_util import AnsiColors


class CustomPusServices(IntEnum):
    SERVICE_200_MODE = 200


class VerificationWrapper:
    def __init__(self, logger: logging.Logger):
        self.pus_verificator = PusVerificator()
        self.logger = logger
        self.with_colors = True

    @property
    def verificator(self) -> PusVerificator:
        return self.pus_verificator

    def add_tc(self, pus_tc: PusTelecommand) -> bool:
        return self.pus_verificator.add_tc(pus_tc)

    def log_to_console(self, srv_1_tm: pus_1.Service1Tm, res: TmCheckResult):
        self.log_to_console_from_req_id(srv_1_tm.tc_req_id, res, srv_1_tm.subservice)

    def log_to_console_from_req_id(
        self,
        req_id: RequestId,
        res: TmCheckResult,
        subservice: Optional[pus_1.Subservices] = None,
    ):
        return self.log_progress_to_console_from_status(res.status, req_id, subservice)

    def log_progress_to_console_from_status(
        self,
        status: VerificationStatus,
        req_id: RequestId,
        subservice: Optional[pus_1.Subservices] = None,
    ):
        acc_char = gen_char_from_status(status.accepted, self.with_colors)
        start_char = gen_char_from_status(status.started, self.with_colors)
        step_char = gen_char_from_status(status.step, self.with_colors)
        fin_char = gen_char_from_status(status.completed, self.with_colors)
        if not status.step_list:
            step_num = 0
        else:
            step_num = max(status.step_list)
        status_str = "Status"
        if subservice is not None:
            if subservice == pus_1.Subservices.TM_ACCEPTANCE_SUCCESS:
                status_str = "Acceptance success"
            elif subservice == pus_1.Subservices.TM_ACCEPTANCE_FAILURE:
                status_str = "Acceptance failure"
            elif subservice == pus_1.Subservices.TM_START_SUCCESS:
                status_str = "Start success"
            elif subservice == pus_1.Subservices.TM_START_FAILURE:
                status_str = "Start failure"
            elif subservice == pus_1.Subservices.TM_STEP_SUCCESS:
                status_str = "Step success"
            elif subservice == pus_1.Subservices.TM_STEP_FAILURE:
                status_str = "Step failure"
            elif subservice == pus_1.Subservices.TM_COMPLETION_SUCCESS:
                status_str = "Completion success"
            elif subservice == pus_1.Subservices.TM_COMPLETION_FAILURE:
                status_str = "Completion failure"
        first_str = f"{status_str} of TC".ljust(25)
        second_str = f"Request ID {req_id.as_u32():#04x}"
        completion_str = ""
        if status.completed == StatusField.SUCCESS:
            completion_str = f" \U0001F31F"
        third_str = (
            f"acc ({acc_char}) sta ({start_char}) ste ({step_char}, {step_num}) "
            f"fin ({fin_char}){completion_str}"
        )
        self.logger.info(f"{first_str} | {second_str} | {third_str}")


def gen_char_from_status(status: StatusField, with_color: bool):
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
