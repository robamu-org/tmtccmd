import time
from collections import deque
from typing import cast
from unittest import TestCase
from datetime import timedelta
from unittest.mock import MagicMock, ANY

from spacepackets.ecss import PusTelecommand
from tmtccmd.com import ComInterface
from tmtccmd.tc.ccsds_seq_sender import SequentialCcsdsSender, SenderMode
from tmtccmd.tc.handler import TcHandlerBase, SendCbParams
from tmtccmd.tc.queue import QueueWrapper, DefaultPusQueueHelper


class TestSendReceive(TestCase):
    def setUp(self) -> None:
        self.queue_wrapper = QueueWrapper(info=None, queue=deque())
        self.queue_helper = DefaultPusQueueHelper(
            self.queue_wrapper,
            tc_sched_timestamp_len=4,
            pus_verificator=None,
            default_pus_apid=None,
            seq_cnt_provider=None,
        )
        self.tc_handler_mock = MagicMock(spec=TcHandlerBase)
        self.com_if = MagicMock(spec=ComInterface)
        self.seq_sender = SequentialCcsdsSender(
            self.queue_wrapper, self.tc_handler_mock
        )

    def test_basic(self):
        res = self.seq_sender.operation(self.com_if)
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
        self.seq_sender.operation(self.com_if)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertIsNone(send_cb_params.info.base)
        raw_tc_entry = send_cb_params.entry.to_raw_tc_entry()
        self.assertEqual(raw_tc_entry.tc, bytes([0, 1, 2]))
        # Queue should be empty now
        # Called twice for each operation call
        self.assertEqual(self.tc_handler_mock.queue_finished_cb.call_count, 2)
        self.assertFalse(self.queue_wrapper.queue)
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
        self.queue_helper.add_raw_tc(bytes([3, 2, 1]))
        self.seq_sender.resume()
        self.assertEqual(self.seq_sender.mode, SenderMode.BUSY)
        res = self.seq_sender.operation(self.com_if)
        self.assertTrue(res.tc_sent)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(send_cb_params.entry.to_raw_tc_entry().tc, bytes([3, 2, 1]))

    def test_with_wait_entry(self):
        wait_delay = 0.01
        self.queue_helper.add_raw_tc(bytes([3, 2, 1]))
        self.queue_helper.add_wait(timedelta(seconds=wait_delay))
        self.queue_helper.add_raw_tc(bytes([1, 2, 3]))
        # Resume call necessary
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
        self.seq_sender.resume()
        res = self.seq_sender.operation(self.com_if)
        self.assertEqual(res.mode, SenderMode.BUSY)
        self.assertTrue(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(send_cb_params.entry.to_raw_tc_entry().tc, bytes([3, 2, 1]))
        self.assertTrue(self.seq_sender.no_delay_remaining())
        # 2 queue entries remaining
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 2)
        # Now the wait entry should be handled
        res = self.seq_sender.operation(self.com_if)
        self.assertFalse(self.seq_sender.no_delay_remaining())
        self.assertFalse(res.tc_sent)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(
            send_cb_params.entry.to_wait_entry().wait_time,
            timedelta(seconds=wait_delay),
        )
        # Now no TCs should be sent for 10 ms
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 1)
        self.assertEqual(res.mode, SenderMode.BUSY)
        res = self.seq_sender.operation(self.com_if)
        self.assertFalse(res.tc_sent)
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 1)
        # After a delay, TC should be sent
        time.sleep(wait_delay)
        res = self.seq_sender.operation(self.com_if)
        self.assertTrue(res.tc_sent)
        self.assertEqual(len(self.queue_helper.queue_wrapper.queue), 0)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(send_cb_params.entry.to_raw_tc_entry().tc, bytes([1, 2, 3]))

    def test_interpacket_delay(self):
        delay_ms = 20
        inter_packet_delay = timedelta(milliseconds=delay_ms)
        ping_cmd = PusTelecommand(service=17, subservice=1)
        self.queue_helper.add_pus_tc(ping_cmd)
        self.queue_helper.add_packet_delay_ms(delay_ms)
        self.queue_helper.add_ccsds_tc(ping_cmd.to_space_packet())
        self.queue_helper.add_raw_tc(bytes([0, 1, 2]))
        # Send first TC, assert delay of 10 ms, then send last packet
        res = self.seq_sender.operation(self.com_if)
        self.assertEqual(res.longest_rem_delay, timedelta())
        self.assertTrue(res.tc_sent)
        self.assertEqual(res.next_entry_is_tc, False)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(send_cb_params.com_if, self.com_if)
        self.assertIsNone(send_cb_params.info.base)
        self.assertEqual(send_cb_params.entry.to_pus_tc_entry().pus_tc, ping_cmd)
        res = self.seq_sender.operation(self.com_if)
        self.assertFalse(res.tc_sent)
        self.assertEqual(res.next_entry_is_tc, True)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertIsNone(send_cb_params.info.base)
        self.assertEqual(
            send_cb_params.entry.to_packet_delay_entry().delay_time.total_seconds(),
            inter_packet_delay.total_seconds(),
        )
        self.assertTrue(
            inter_packet_delay * 0.8 <= res.longest_rem_delay <= inter_packet_delay
        )
        res = self.seq_sender.operation(self.com_if)
        # No TC sent
        self.assertFalse(res.tc_sent)
        self.assertEqual(res.next_entry_is_tc, True)
        self.assertEqual(len(self.queue_wrapper.queue), 2)
        time.sleep(inter_packet_delay.total_seconds())
        res = self.seq_sender.operation(self.com_if)
        # TC sent
        self.assertTrue(res.tc_sent)
        self.assertEqual(len(self.queue_wrapper.queue), 1)
        res = self.seq_sender.operation(self.com_if)
        # No TC sent, delay after each packet
        self.assertFalse(res.tc_sent)
        self.assertEqual(len(self.queue_wrapper.queue), 1)
        self.assertTrue(
            0.8 * inter_packet_delay < res.longest_rem_delay <= inter_packet_delay
        )
        # Delay 10 ms
        time.sleep(inter_packet_delay.total_seconds())
        res = self.seq_sender.operation(self.com_if)
        self.assertTrue(res.tc_sent)
        # Queue is empty now, but this should still be set to False
        self.assertEqual(res.next_entry_is_tc, False)
        self.tc_handler_mock.send_cb.assert_called_with(ANY)
        call_args = self.tc_handler_mock.send_cb.call_args
        send_cb_params = cast(SendCbParams, call_args.args[0])
        self.assertEqual(send_cb_params.entry.to_raw_tc_entry().tc, bytes([0, 1, 2]))

    def test_delay_at_end(self):
        delay_at_end = timedelta(milliseconds=20)
        self.queue_helper.add_raw_tc(bytes([3, 2, 1]))
        self.queue_helper.add_wait(delay_at_end)
        self.seq_sender.resume()
        res = self.seq_sender.operation(self.com_if)
        self.assertTrue(res.tc_sent)
        self.assertEqual(res.longest_rem_delay, timedelta())
        res = self.seq_sender.operation(self.com_if)
        self.assertFalse(res.tc_sent)
        self.assertFalse(self.seq_sender.no_delay_remaining())
        self.assertTrue(0.8 * delay_at_end < res.longest_rem_delay <= delay_at_end)
        self.assertEqual(self.seq_sender.mode, SenderMode.BUSY)
        time.sleep(delay_at_end.total_seconds())
        self.assertTrue(self.seq_sender.no_delay_remaining())
        self.seq_sender.operation(self.com_if)
        self.assertEqual(self.seq_sender.mode, SenderMode.DONE)
