from collections import deque
from unittest import TestCase
from unittest.mock import MagicMock

from spacepackets.ecss import PusTelemetry
from spacepackets.ccsds.time import CdsShortTimestamp
from tmtccmd.tm import (
    SpecificApidHandlerBase,
    CcsdsTmHandler,
    GenericApidHandlerBase,
)
from tmtccmd.com import ComInterface
from tmtccmd.tm.ccsds_tm_listener import CcsdsTmListener


class ApidHandler(SpecificApidHandlerBase):
    def __init__(self, apid: int):
        super().__init__(apid, None)
        self.was_called = False
        self.called_times = 0
        self.packet_queue = deque()

    def handle_tm(self, packet: bytes, user_args: any):
        if not self.was_called:
            self.was_called = True
        self.called_times += 1
        self.packet_queue.appendleft(packet)


class TestTmHandler(TestCase):
    def test_basic(self):
        tm_handler = ApidHandler(0x01)
        com_if = MagicMock(specs=ComInterface)
        unknown_handler = MagicMock(specs=GenericApidHandlerBase)
        ccsds_handler = CcsdsTmHandler(unknown_handler)
        ccsds_handler.add_apid_handler(tm_handler)
        tm_listener = CcsdsTmListener(tm_handler=ccsds_handler)
        handled_packets = tm_listener.operation(com_if)
        self.assertEqual(handled_packets, 0)
        self.assertTrue(ccsds_handler.has_apid(0x01))
        tm0_raw = PusTelemetry(
            service=1, subservice=12, apid=0x01, time_provider=CdsShortTimestamp.empty()
        ).pack()
        tm1_raw = PusTelemetry(
            service=5, subservice=1, apid=0x01, time_provider=CdsShortTimestamp.empty()
        ).pack()
        com_if.receive.return_value = [tm0_raw]
        handled_packets = tm_listener.operation(com_if)
        self.assertEqual(handled_packets, 1)
        self.assertTrue(tm_handler.was_called)
        self.assertEqual(tm_handler.called_times, 1)
        self.assertEqual(tm_handler.packet_queue.pop(), tm0_raw)
        com_if.receive.return_value = [tm0_raw, tm1_raw]
        handled_packets = tm_listener.operation(com_if)
        self.assertEqual(handled_packets, 2)
        self.assertEqual(tm_handler.called_times, 3)
        self.assertEqual(handled_packets, 2)
        self.assertEqual(tm_handler.packet_queue.pop(), tm0_raw)
        self.assertEqual(tm_handler.packet_queue.pop(), tm1_raw)
        unknown_apid = PusTelemetry(
            service=1, subservice=12, apid=0x02, time_provider=CdsShortTimestamp.empty()
        ).pack()
        com_if.receive.return_value = [unknown_apid]
        handled_packets = tm_listener.operation(com_if)
        self.assertEqual(handled_packets, 1)
        unknown_handler.handle_tm.assert_called_once()
