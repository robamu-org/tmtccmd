from typing import Optional
from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import (
    create_acceptance_success_tm,
    RequestId,
    create_start_success_tm,
    create_step_success_tm,
    StepId,
    create_completion_success_tm,
)
from tmtccmd.pus.pus_verificator import PusVerificator, StatusField, VerificationStatus


class TestPusVerificator(TestCase):
    def setUp(self) -> None:
        self.pus_verificator = PusVerificator()
        self.ping_tc = PusTelecommand(service=17, subservice=1)
        self.req_id = RequestId.from_pus_tc(self.ping_tc)
        self.acc_suc_tm = create_acceptance_success_tm(self.ping_tc)
        self.sta_suc_tm = create_start_success_tm(self.ping_tc)
        self.ste_suc_tm = create_step_success_tm(
            self.ping_tc, step_id=StepId.from_byte_size(1, 1)
        )
        self.fin_suc_tm = create_completion_success_tm(self.ping_tc)

    def test_basic(self):
        self.pus_verificator.add_tc(self.ping_tc)
        check_res = self.pus_verificator.add_tm(self.acc_suc_tm)
        self.assertEqual(check_res.completed, False)
        status = check_res.status
        self._check_status(
            status, False, StatusField.SUCCESS, StatusField.UNSET, 0, StatusField.UNSET
        )
        verif_dict = self.pus_verificator.verif_dict
        self.assertEqual(len(verif_dict), 1)
        for key, val in verif_dict.items():
            self.assertEqual(key, self.req_id)
            self._check_status(
                val, False, StatusField.SUCCESS, StatusField.UNSET, 0, StatusField.UNSET
            )

    def test_complete_verification(self):
        self.pus_verificator.add_tc(self.ping_tc)
        acc_tm = create_acceptance_success_tm(self.ping_tc)
        check_res = self.pus_verificator.add_tm(self.acc_suc_tm)
        status = check_res.status
        self._check_status(
            status, False, StatusField.SUCCESS, StatusField.UNSET, 0, StatusField.UNSET
        )
        check_res = self.pus_verificator.add_tm(self.sta_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            0,
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(self.ste_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            1,
            StatusField.UNSET,
        )

    def _check_status(
        self,
        status: Optional[VerificationStatus],
        all_verifs: bool,
        acc_st: StatusField,
        sta_st: StatusField,
        steps: int,
        fin_st: StatusField,
    ):
        self.assertIsNotNone(status)
        self.assertEqual(status.all_verifs_recvd, all_verifs)
        self.assertEqual(status.accepted, acc_st)
        self.assertEqual(status.step, steps)
        self.assertEqual(status.started, sta_st)
        self.assertEqual(status.completed, fin_st)
