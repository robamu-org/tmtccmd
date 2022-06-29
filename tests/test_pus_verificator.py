from unittest import TestCase

from tmtccmd.utility.conf_util import AnsiColors


class TestPusVerificator(TestCase):
    def test_basic(self):
        # pus_verificator = PusVerificator()
        # pus_verificator.add_tc()
        # pus_verificator.add_tm()
        # verif_dict = wpus_verificator.verif_dict
        print(
            f"{AnsiColors.GREEN}\u2714{AnsiColors.GREEN}\u27140{AnsiColors.GREEN}\u2714"
        )
