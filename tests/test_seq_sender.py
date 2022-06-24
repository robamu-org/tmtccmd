from collections import deque
from unittest import TestCase
from unittest.mock import MagicMock, ANY

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.tc.ccsds_seq_sender import SequentialCcsdsSender, SenderMode
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper, QueueHelper


class TestSendReceive(TestCase):
    def test_basic(self):
        queue_wrapper = QueueWrapper(queue=deque())
        queue_helper = QueueHelper(queue_wrapper)
        tc_handler_mock = MagicMock(spec=TcHandlerBase)
        com_if = MagicMock(spec=CommunicationInterface)
        seq_sender = SequentialCcsdsSender(queue_wrapper, com_if, tc_handler_mock)
        res = seq_sender.operation()
        # Queue is empty initially
        self.assertEqual(res.mode, SenderMode.DONE)
        self.assertEqual(seq_sender.mode, SenderMode.DONE)
        self.assertTrue(seq_sender.no_delay_remaining())
        queue_helper.add_raw_tc(bytes([0, 1, 2]))
        # One queue entry which should be handled immediately
        seq_sender.queue_wrapper = queue_wrapper
        self.assertEqual(seq_sender.mode, SenderMode.BUSY)
        # Is busy now, so does not accept new queue unless forced
        with self.assertRaises(ValueError):
            seq_sender.queue_wrapper = queue_wrapper
        seq_sender.operation()
        tc_handler_mock.send_cb.assert_called_with(ANY, com_if)
        call_args = tc_handler_mock.send_cb.call_args
        print(call_args)
        self.assertEqual(call_args.args[0].tc, bytes([0, 1, 2]))
        # Queue should be empty now
        self.assertFalse(queue_wrapper.queue)
        self.assertEqual(seq_sender.mode, SenderMode.DONE)
        queue_helper.add_raw_tc(bytes([3, 2, 1]))
        seq_sender.resume()
        self.assertEqual(seq_sender.mode, SenderMode.BUSY)
        queue_helper.add_wait(0.1)
        queue_helper.add_raw_tc(bytes([1, 2, 3]))
        res = seq_sender.operation()
        self.assertEqual(res.mode, SenderMode.BUSY)
        tc_handler_mock.send_cb.assert_called_with(ANY, com_if)
        call_args = tc_handler_mock.send_cb.call_args
        self.assertEqual(call_args.args[0].tc, bytes([3, 2, 1]))
