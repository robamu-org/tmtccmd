import time
from collections import deque
from unittest import TestCase
from unittest.mock import MagicMock, ANY

from spacepackets.ecss import PusTelecommand
from tmtccmd.com_if import ComInterface
from tmtccmd.tc.ccsds_seq_sender import SequentialCcsdsSender, SenderMode
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper, QueueHelper


class TestSendReceive(TestCase):
    def setUp(self) -> None:
        self.queue_wrapper = QueueWrapper(info=None, queue=deque())
        self.queue_helper = QueueHelper(self.queue_wrapper)
        self.tc_handler_mock = MagicMock(spec=TcHandlerBase)
        self.com_if = MagicMock(spec=ComInterface)
        self.seq_sender = SequentialCcsdsSender(
            self.queue_wrapper, self.com_if, self.tc_handler_mock
        )

    def test_basic(self):
        res = self.seq_sender.operation()
        # Queue is empty initially
        self.assertEqual(res.mode, SenderMode.DONE)
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
        self.assertTrue(self.seq_sender.no_delay_remaining())
        self.queue_helper.add_raw_tc(bytes([0, 1, 2]))
        # One queue entry which should be handled immediately
        self.seq_sender.queue_wrapper = self.queue_wrapper
        self.assertEqual(self.seq_sender.mode, SenderMode.BUSY)
        # Is busy now, so does not accept new queue unless forced
        with self.assertRaises(ValueError):
            self.seq_sender.queue_wrapper = self.queue_wrapper
        self.seq_sender.operation()
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([0, 1, 2]))
        # Queue should be empty now
        # Called twice for each operation call
        self.assertEqual(self.tc_handler_mock.queue_finished_cb.call_count, 2)
        self.assertFalse(self.queue_wrapper.queue)
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
        self.queue_helper.add_raw_tc(bytes([3, 2, 1]))
        self.seq_sender.resume()
        self.assertEqual(self.seq_sender.mode, SenderMode.BUSY)
        res = self.seq_sender.operation()
        self.assertTrue(res.tc_sent)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([3, 2, 1]))

    def test_with_wait_entry(self):
        wait_delay = 0.01
        self.queue_helper.add_raw_tc(bytes([3, 2, 1]))
        self.queue_helper.add_wait(wait_delay)
        self.queue_helper.add_raw_tc(bytes([1, 2, 3]))
        # Resume call necessary
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
        self.seq_sender.resume()
        res = self.seq_sender.operation()
        self.assertEqual(res.mode, SenderMode.BUSY)
        self.assertTrue(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([3, 2, 1]))
        self.assertTrue(self.seq_sender.no_delay_remaining())
        # 2 queue entries remaining
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 2)
        # Now the wait entry should be handled
        res = self.seq_sender.operation()
        self.assertFalse(self.seq_sender.no_delay_remaining())
        self.assertFalse(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].wait_secs, wait_delay)
        # Now no TCs should be sent for 10 ms
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 1)
        self.assertEqual(res.mode, SenderMode.BUSY)
        res = self.seq_sender.operation()
        self.assertFalse(res.tc_sent)
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 1)
        # After a delay, TC should be sent
        time.sleep(wait_delay)
        res = self.seq_sender.operation()
        self.assertTrue(res.tc_sent)
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 0)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([1, 2, 3]))

    def test_interpacket_delay(self):
        inter_packet_delay = 0.02
        ping_cmd = PusTelecommand(service=17, subservice=1)
        self.queue_helper.add_pus_tc(ping_cmd)
        self.queue_helper.add_packet_delay(inter_packet_delay)
        self.queue_helper.add_ccsds_tc(ping_cmd.to_space_packet())
        self.queue_helper.add_raw_tc(bytes([0, 1, 2]))
        # Send first TC, assert delay of 10 ms, then send last packet
        res = self.seq_sender.operation()
        self.assertEqual(res.longest_rem_delay, 0.0)
        self.assertTrue(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].pus_tc.pack(), ping_cmd.pack())
        res = self.seq_sender.operation()
        self.assertFalse(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].delay_secs, inter_packet_delay)
        self.assertTrue(0.8 * inter_packet_delay < res.longest_rem_delay < inter_packet_delay)
        res = self.seq_sender.operation()
        # No TC sent
        self.assertFalse(res.tc_sent)
        self.assertEqual(len(self.queue_wrapper.queue), 2)
        time.sleep(inter_packet_delay * 1.1)
        res = self.seq_sender.operation()
        # TC sent
        self.assertTrue(res.tc_sent)
        self.assertEqual(len(self.queue_wrapper.queue), 1)
        res = self.seq_sender.operation()
        # No TC sent, delay after each packet
        self.assertFalse(res.tc_sent)
        self.assertEqual(len(self.queue_wrapper.queue), 1)
        self.assertTrue(0.8 * inter_packet_delay < res.longest_rem_delay < inter_packet_delay)
        # Delay 10 ms
        time.sleep(inter_packet_delay)
        res = self.seq_sender.operation()
        self.assertTrue(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY, self.com_if)
        call_args = self.tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([0, 1, 2]))
