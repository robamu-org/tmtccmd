import math
from collections import deque
from typing import cast
from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from tmtccmd.tc.definitions import WaitEntry, CastWrapper
from tmtccmd.tc.queue import QueueWrapper, QueueHelper


class TestTcQueue(TestCase):
    def test_queue(self):
        queue_wrapper = QueueWrapper(queue=deque())
        self.assertEqual(queue_wrapper.queue, deque())
        queue_helper = QueueHelper(queue_wrapper)
        queue_helper.add_wait(2.0)
        self.assertEqual(len(queue_wrapper.queue), 1)
        wait_entry = cast(WaitEntry, queue_wrapper.queue.pop())
        self.assertTrue(wait_entry)
        self.assertTrue(
            math.isclose(wait_entry.wait_time, eval(f"{wait_entry!r}").wait_time)
        )
        self.assertEqual(wait_entry.wait_time, 2.0)
        self.assertEqual(len(queue_wrapper.queue), 0)
        pus_cmd = PusTelecommand(service=17, subservice=1)
        queue_helper.add_pus_tc(pus_cmd)
        self.assertEqual(len(queue_wrapper.queue), 1)
        queue_helper.add_log_cmd("Test String")
        queue_helper.add_raw_tc(bytes([0, 1, 2]))
        queue_helper.add_ccsds_tc(pus_cmd.to_space_packet())
        self.assertEqual(len(queue_wrapper.queue), 4)

        pus_entry = queue_wrapper.queue.pop()
        cast_wrapper = CastWrapper(pus_entry)
        pus_entry = cast_wrapper.to_pus_tc_entry()
        print(pus_entry.pus_tc)
