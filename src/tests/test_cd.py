import time
from unittest import TestCase
from tmtccmd.utility.countdown import Countdown


class CountdownTest(TestCase):
    def test_basic(self):
        test_cd = Countdown(init_timeout_secs=0.05)
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
        self.assertTrue(test_cd.rem_time() > 0)
        time.sleep(0.05)
        self.assertTrue(test_cd.timed_out())
        self.assertTrue(test_cd.rem_time() == 0)
        test_cd.timeout = 0.1
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
        time.sleep(0.1)
        self.assertTrue(test_cd.timed_out())
        test_cd.reset(0.05)
        self.assertTrue(test_cd.rem_time() > 0.045)
        self.assertTrue(test_cd.busy())
        self.assertFalse(test_cd.timed_out())
