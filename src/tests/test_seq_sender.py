from collections import deque
from unittest import TestCase
from unittest.mock import MagicMock

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.tc.ccsds_seq_sender import SequentialCcsdsSender
from tmtccmd.tc.handler import TcHandlerBase
from tmtccmd.tc.queue import QueueWrapper, QueueHelper


class TestSendReceive(TestCase):
    def basic_test(self):
        queue_wrapper = QueueWrapper(queue=deque())
        queue_helper = QueueHelper(queue_wrapper)
        tc_handler_mock = MagicMock(spec=TcHandlerBase)
        com_if = MagicMock(spec=CommunicationInterface)
        seq_sender = SequentialCcsdsSender(queue_wrapper, com_if, tc_handler_mock)
        res = seq_sender.operation()
