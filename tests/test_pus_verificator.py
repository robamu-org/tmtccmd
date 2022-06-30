from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import (
    Service1Tm,
    create_acceptance_success_tm,
    RequestId,
)
from tmtccmd.pus.pus_verificator import PusVerificator, StatusField
from tmtccmd.utility.conf_util import AnsiColors


class TestPusVerificator(TestCase):
    def test_basic(self):
        pus_verificator = PusVerificator()
        ping_tc = PusTelecommand(service=17, subservice=1)
        req_id = RequestId.from_pus_tc(ping_tc)
        pus_verificator.add_tc(ping_tc)
        ping_tm = create_acceptance_success_tm(ping_tc)
        check_res = pus_verificator.add_tm(ping_tm)
        self.assertEqual(check_res.completed, False)
        status = check_res.status
        self.assertNotEqual(status, None)
        self.assertEqual(status.accepted, StatusField.SUCCESS)
        self.assertEqual(status.all_verifs_recvd, False)
        self.assertEqual(status.started, StatusField.UNSET)
        self.assertEqual(status.step, 0)
        self.assertEqual(status.completed, StatusField.UNSET)
        verif_dict = pus_verificator.verif_dict
        self.assertEqual(len(verif_dict), 1)
        for key, val in verif_dict.items():
            self.assertEqual(key, req_id)
            self.assertEqual(val.accepted, StatusField.SUCCESS)
            self.assertEqual(val.all_verifs_recvd, False)
            self.assertEqual(val.started, StatusField.UNSET)
            self.assertEqual(val.step, 0)
            self.assertEqual(val.completed, StatusField.UNSET)
        print(
            f"{AnsiColors.GREEN}\u2714{AnsiColors.GREEN}\u27140{AnsiColors.GREEN}\u2714"
        )
