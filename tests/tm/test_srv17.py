#!/usr/bin/env python3
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_17_test import Service17Tm


class TestTelemetry(TestCase):
    def setUp(self) -> None:
        self.pus_17_telemetry = Service17Tm(
            subservice=1,
            ssc=36,
            time_provider=CdsShortTimestamp.from_now(),
            apid=0xEF,
        )

        self.pus_17_raw = self.pus_17_telemetry.pack()

    def test_generic_pus_c(self):
        def tm_func(raw_telemetry: bytearray):
            return Service17Tm.unpack(
                data=raw_telemetry, time_reader=CdsShortTimestamp.empty()
            )

        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises(ValueError, tm_func, None)

        pus_17_telemetry = Service17Tm.unpack(
            data=self.pus_17_raw, time_reader=CdsShortTimestamp.empty()
        )
        self.assertTrue(pus_17_telemetry.service == 17)
        self.assertTrue(pus_17_telemetry.apid == 0xEF)
        self.assertTrue(pus_17_telemetry.subservice == 1)
        self.assertTrue(pus_17_telemetry.seq_count == 36)
        self.assertTrue(pus_17_telemetry.source_data == bytearray())
        self.assertTrue(pus_17_telemetry.pus_tm.packet_id.raw() == 0x8 << 8 | 0xEF)
