from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from tmtccmd.tm.pus_200_fsfw_mode import Service200FsfwTm
from tmtccmd.pus.s200_fsfw_mode_defs import Subservice


class TestSrv200Tm(TestCase):
    def setUp(self):
        self.srv_200_tm = Service200FsfwTm(
            subservice_id=Subservice.TM_MODE_REPLY,
            object_id=bytes([0x01, 0x02, 0x03, 0x04]),
            time=CdsShortTimestamp.empty(),
            apid=0x02,
        )

    def test_serialization(self):
        raw_packet = self.srv_200_tm.pack()
        self.assertEqual(raw_packet[7], 200)
        self.assertEqual(raw_packet[8], Subservice.TM_MODE_REPLY)

    def test_deserialization(self):
        raw_packet = self.srv_200_tm.pack()
        srv_200_tm = Service200FsfwTm.unpack(raw_packet, CdsShortTimestamp.empty())
        self.assertEqual(srv_200_tm.pack(), raw_packet)
