from typing import Optional, List
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


class TestSuccessSet:
    def __init__(self, pus_tc: PusTelecommand):
        self.pus_tc = pus_tc
        self.req_id = RequestId.from_pus_tc(pus_tc)
        self.acc_suc_tm = create_acceptance_success_tm(pus_tc)
        self.sta_suc_tm = create_start_success_tm(pus_tc)
        self.ste_suc_tm = create_step_success_tm(
            pus_tc, step_id=StepId.from_byte_size(1, 1)
        )
        self.fin_suc_tm = create_completion_success_tm(pus_tc)


class TestPusVerificator(TestCase):
    def setUp(self) -> None:
        self.pus_verificator = PusVerificator()

    def test_basic(self):
        suc_set = TestSuccessSet(PusTelecommand(service=17, subservice=1))
        self.pus_verificator.add_tc(suc_set.pus_tc)
        check_res = self.pus_verificator.add_tm(suc_set.acc_suc_tm)
        self.assertEqual(check_res.completed, False)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        verif_dict = self.pus_verificator.verif_dict
        self.assertEqual(len(verif_dict), 1)
        for key, val in verif_dict.items():
            self.assertEqual(key, suc_set.req_id)
            self._check_status(
                val,
                False,
                StatusField.SUCCESS,
                StatusField.UNSET,
                StatusField.UNSET,
                [],
                StatusField.UNSET,
            )

    def test_complete_verification_clear_completed(self):
        self._regular_success_seq(
            TestSuccessSet(PusTelecommand(service=17, subservice=1))
        )
        self.pus_verificator.remove_completed_entries()
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_complete_verification_clear_completed_multi(self):
        self._regular_success_seq(
            TestSuccessSet(PusTelecommand(service=17, subservice=1, seq_count=0))
        )
        self._regular_success_seq(
            TestSuccessSet(PusTelecommand(service=5, subservice=4, seq_count=1))
        )
        self.pus_verificator.remove_completed_entries()
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def test_complete_verification_remove_manually(self):
        suc_set = TestSuccessSet(PusTelecommand(service=17, subservice=1))
        self._regular_success_seq(suc_set)
        self.pus_verificator.remove_entry(suc_set.req_id)
        self.assertEqual(len(self.pus_verificator.verif_dict), 0)

    def _regular_success_seq(self, suc_set: TestSuccessSet):
        self.pus_verificator.add_tc(suc_set.pus_tc)
        check_res = self.pus_verificator.add_tm(suc_set.acc_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.UNSET,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.sta_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.UNSET,
            [],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.ste_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            False,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            [1],
            StatusField.UNSET,
        )
        check_res = self.pus_verificator.add_tm(suc_set.fin_suc_tm)
        status = check_res.status
        self._check_status(
            status,
            True,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            StatusField.SUCCESS,
            [1],
            StatusField.SUCCESS,
        )

    def _check_status(
        self,
        status: Optional[VerificationStatus],
        all_verifs: bool,
        acc_st: StatusField,
        sta_st: StatusField,
        step_st: StatusField,
        step_list: List[int],
        fin_st: StatusField,
    ):
        self.assertIsNotNone(status)
        self.assertEqual(status.all_verifs_recvd, all_verifs)
        self.assertEqual(status.accepted, acc_st)
        self.assertEqual(status.step, step_st)
        self.assertEqual(status.step_list, step_list)
        self.assertEqual(status.started, sta_st)
        self.assertEqual(status.completed, fin_st)
