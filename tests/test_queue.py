import math
from collections import deque
from datetime import timedelta
from typing import cast
from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from tmtccmd.tc import WaitEntry, QueueEntryHelper

# Required for eval calls
# noinspection PyUnresolvedReferences
from tmtccmd.tc import LogQueueEntry, RawTcEntry
from tmtccmd.tc.queue import QueueWrapper, QueueHelper


class TestTcQueue(TestCase):
    def test_queue(self):
        queue_wrapper = QueueWrapper(info=None, queue=deque())
        self.assertEqual(queue_wrapper.queue, deque())
        queue_helper = QueueHelper(queue_wrapper)
        queue_helper.add_wait(timedelta(seconds=2))
        self.assertEqual(len(queue_wrapper.queue), 1)
        wait_entry = cast(WaitEntry, queue_wrapper.queue.pop())
        self.assertTrue(wait_entry)
        self.assertFalse(wait_entry.is_tc())
        self.assertEqual(wait_entry.wait_time.total_seconds(), 2.0)
        self.assertEqual(len(queue_wrapper.queue), 0)
        pus_cmd = PusTelecommand(service=17, subservice=1)
        queue_helper.add_pus_tc(pus_cmd)
        self.assertEqual(len(queue_wrapper.queue), 1)
        queue_helper.add_log_cmd("Test String")
        queue_helper.add_raw_tc(bytes([0, 1, 2]))
        queue_helper.add_ccsds_tc(pus_cmd.to_space_packet())
        queue_helper.add_packet_delay(timedelta(seconds=3.0))
        print(queue_wrapper.queue)
        self.assertEqual(len(queue_wrapper.queue), 5)

        pus_entry = queue_wrapper.queue.popleft()
        self.assertTrue(pus_entry.is_tc())
        cast_wrapper = QueueEntryHelper(pus_entry)
        pus_entry = cast_wrapper.to_pus_tc_entry()
        self.assertEqual(pus_entry.pus_tc, pus_cmd)
        self.assertTrue(pus_entry)
        with self.assertRaises(TypeError):
            cast_wrapper.to_wait_entry()
        log_entry = queue_wrapper.queue.popleft()
        self.assertFalse(log_entry.is_tc())
        cast_wrapper.base = log_entry
        log_entry = cast_wrapper.to_log_entry()
        self.assertTrue(log_entry)
        with self.assertRaises(TypeError):
            cast_wrapper.to_raw_tc_entry()
        self.assertEqual(log_entry.log_str, "Test String")
        test_obj = eval(f"{log_entry!r}")
        self.assertEqual(test_obj.log_str, log_entry.log_str)

        raw_entry = queue_wrapper.queue.popleft()
        self.assertTrue(raw_entry.is_tc())
        cast_wrapper.base = raw_entry
        raw_entry = cast_wrapper.to_raw_tc_entry()
        self.assertTrue(raw_entry)
        self.assertEqual(raw_entry.tc, bytes([0, 1, 2]))
        test_obj = eval(f"{raw_entry!r}")
        self.assertEqual(raw_entry.tc, test_obj.tc)

        space_packet_entry = queue_wrapper.queue.popleft()
        self.assertTrue(space_packet_entry.is_tc())
        cast_wrapper.base = space_packet_entry
        space_packet_entry = cast_wrapper.to_space_packet_entry()
        self.assertTrue(space_packet_entry)
        self.assertTrue(space_packet_entry.space_packet, pus_cmd.to_space_packet())

        packet_delay = queue_wrapper.queue.pop()
        self.assertFalse(packet_delay.is_tc())
        cast_wrapper.base = packet_delay
        packet_delay = cast_wrapper.to_packet_delay_entry()
        self.assertEqual(packet_delay.delay_time.total_seconds(), 3.0)
