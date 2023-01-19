import os
from pathlib import Path
from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import (
    create_acceptance_success_tm,
    create_start_success_tm,
    create_step_success_tm,
    StepId,
    create_completion_success_tm,
    create_acceptance_failure_tm,
    FailureNotice,
    ErrorCode,
    create_start_failure_tm,
)
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_verificator import PusVerificator
from tmtccmd import get_console_logger
from tmtccmd.logging.pus import RegularTmtcLogWrapper
from tmtccmd.pus import VerificationWrapper


class TestPusVerifLog(TestCase):
    def setUp(self) -> None:
        self.log_file_name = RegularTmtcLogWrapper.get_current_tmtc_file_name()

    def test_console_log_success(self):
        logger = get_console_logger()
        wrapper = VerificationWrapper(PusVerificator(), logger, None)
        self._test_success(wrapper)

    def test_console_log_success_without_colors(self):
        logger = get_console_logger()
        wrapper = VerificationWrapper(PusVerificator(), logger, None)
        wrapper.with_colors = False
        self._test_success(wrapper)

    def _test_success(self, wrapper: VerificationWrapper):
        verificator = wrapper.verificator
        tc = PusTelecommand(service=17, subservice=1, seq_count=0)
        verificator.add_tc(tc)
        srv_1_tm = create_acceptance_success_tm(
            tc, time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)
        srv_1_tm = create_start_success_tm(tc, time_provider=CdsShortTimestamp.empty())
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)
        srv_1_tm = create_step_success_tm(
            tc, StepId.with_byte_size(1, 1), time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)
        srv_1_tm = create_completion_success_tm(
            tc, time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)

    def test_console_log_acc_failure(self):
        logger = get_console_logger()
        wrapper = VerificationWrapper(PusVerificator(), logger, None)
        self._test_acc_failure(wrapper)

    def test_console_log_acc_failure_without_colors(self):
        logger = get_console_logger()
        wrapper = VerificationWrapper(PusVerificator(), logger, None)
        wrapper.with_colors = False
        self._test_acc_failure(wrapper)

    def _test_acc_failure(self, wrapper: VerificationWrapper):
        verificator = wrapper.verificator
        tc = PusTelecommand(service=17, subservice=1, seq_count=1)
        verificator.add_tc(tc)
        srv_1_tm = create_acceptance_failure_tm(
            tc,
            failure_notice=FailureNotice(code=ErrorCode(pfc=8, val=1), data=bytes()),
            time_provider=CdsShortTimestamp.empty(),
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)

    def test_console_log_start_failure(self):
        logger = get_console_logger()
        wrapper = VerificationWrapper(PusVerificator(), logger, None)
        verificator = wrapper.verificator
        tc = PusTelecommand(service=17, subservice=1, seq_count=2)
        verificator.add_tc(tc)
        srv_1_tm = create_acceptance_failure_tm(
            tc,
            failure_notice=FailureNotice(code=ErrorCode(pfc=8, val=1), data=bytes()),
            time_provider=CdsShortTimestamp.empty(),
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)
        srv_1_tm = create_start_failure_tm(
            tc,
            failure_notice=FailureNotice(code=ErrorCode(pfc=8, val=1), data=bytes()),
            time_provider=CdsShortTimestamp.empty(),
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_console(srv_1_tm, res)

    def test_file_logger(self):
        tmtc_logger = RegularTmtcLogWrapper(self.log_file_name)
        wrapper = VerificationWrapper(PusVerificator(), None, tmtc_logger.logger)
        verificator = wrapper.verificator
        tc = PusTelecommand(service=17, subservice=1, seq_count=0)
        verificator.add_tc(tc)
        srv_1_tm = create_acceptance_success_tm(
            tc, time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_file(srv_1_tm, res)
        srv_1_tm = create_start_success_tm(tc, time_provider=CdsShortTimestamp.empty())
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_file(srv_1_tm, res)
        srv_1_tm = create_step_success_tm(
            tc, StepId.with_byte_size(1, 1), time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_file(srv_1_tm, res)
        srv_1_tm = create_completion_success_tm(
            tc, time_provider=CdsShortTimestamp.empty()
        )
        res = verificator.add_tm(srv_1_tm)
        wrapper.log_to_file(srv_1_tm, res)
        # Assert that 4 lines have been written
        with open(self.log_file_name) as file:
            all_lines = file.readlines()
            self.assertEqual(len(all_lines), 4)

    def tearDown(self) -> None:
        log_file = Path(self.log_file_name)
        if log_file.exists():
            os.remove(log_file)
