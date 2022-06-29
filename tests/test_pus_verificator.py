from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import Service1Tm
from tmtccmd.pus.pus_verificator import PusVerificator
from tmtccmd.utility.conf_util import AnsiColors


class TestPusVerificator(TestCase):
    def test_basic(self):
        pus_verificator = PusVerificator()
        ping_tc = PusTelecommand(service=17, subservice=1)
        pus_verificator.add_tc(ping_tc)
        # ping_tm = Service1Tm()
        # pus_verificator.add_tm()
        verif_dict = pus_verificator.verif_dict
        print(
            f"{AnsiColors.GREEN}\u2714{AnsiColors.GREEN}\u27140{AnsiColors.GREEN}\u2714"
        )
