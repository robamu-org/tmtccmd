import struct
from unittest import TestCase
from tmtccmd.tm.pus_5_fsfw_event import Service5Tm, Subservice, EventDefinition


class TestSrv5Tm(TestCase):
    def setUp(self):
        self.obj_id = bytes([0x00, 0x01, 0x02, 0x03])
        self.event_def = EventDefinition(
            event_id=5, reporter_id=self.obj_id, param1=22, param2=942
        )
        self.srv5_tm = Service5Tm(
            subservice=Subservice.TM_INFO_EVENT,
            event=self.event_def,
            time_provider=None,
        )

    def test_basic(self):
        self.assertEqual(
            self.srv5_tm.sp_header, self.srv5_tm.pus_tm.space_packet_header
        )
        self.assertEqual(self.srv5_tm.service, 5)
        self.assertEqual(self.srv5_tm.subservice, Subservice.TM_INFO_EVENT)
        self.assertEqual(len(self.srv5_tm.source_data), 14)

    def test_packed(self):
        raw_tm = self.srv5_tm.pack()
        self.assertEqual(raw_tm[7], 5)
        self.assertEqual(raw_tm[8], Subservice.TM_INFO_EVENT)
        self.assertEqual(struct.unpack("!H", raw_tm[13:15])[0], 5)
        self.assertEqual(raw_tm[15:19], self.obj_id)
        self.assertEqual(struct.unpack("!I", raw_tm[19:23])[0], 22)
        self.assertEqual(struct.unpack("!I", raw_tm[23:27])[0], 942)

    def test_unpack(self):
        raw_tm = self.srv5_tm.pack()
        unpacked = Service5Tm.unpack(raw_tm, None)
        self.assertEqual(self.srv5_tm, unpacked)
        self.assertEqual(unpacked.event_definition, self.event_def)
