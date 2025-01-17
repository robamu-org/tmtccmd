#:wq/usr/bin/env python3
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_17_test import Service17Tm


class TestTelemetry(TestCase):
    def setUp(self) -> None:
        self.apid = 0xEF
        self.pus_17_telemetry = Service17Tm(
            apid=self.apid,
            subservice=1,
            ssc=36,
            timestamp=CdsShortTimestamp.now().pack(),
        )

        self.pus_17_raw = self.pus_17_telemetry.pack()

    def test_generic_pus_c(self):
        def tm_func(raw_telemetry: bytearray):
            return Service17Tm.unpack(data=raw_telemetry, timestamp_len=7)

        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises((TypeError, ValueError), tm_func, None)

        pus_17_telemetry = Service17Tm.unpack(data=self.pus_17_raw, timestamp_len=7)
        self.assertTrue(pus_17_telemetry.service == 17)
        self.assertTrue(pus_17_telemetry.apid == 0xEF)
        self.assertTrue(pus_17_telemetry.subservice == 1)
        self.assertTrue(pus_17_telemetry.seq_count == 36)
        self.assertTrue(pus_17_telemetry.source_data == bytearray())
        self.assertTrue(pus_17_telemetry.pus_tm.packet_id.raw() == 0x8 << 8 | 0xEF)
