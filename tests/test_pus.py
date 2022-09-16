#!/usr/bin/env python3
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_17_test import Service17Tm
from spacepackets.util import PrintFormats

from tmtccmd.tm.pus_17_test import Service17TmExtended


class TestTelemetry(TestCase):
    def test_generic_pus_c(self):
        pus_17_telemetry = Service17Tm(
            subservice=1,
            ssc=36,
            time_provider=CdsShortTimestamp.from_current_time(),
            apid=0xEF,
        )
        pus_17_raw = pus_17_telemetry.pack()

        pus_17_telemetry = None

        def tm_func(raw_telemetry: bytearray):
            return Service17Tm.unpack(raw_telemetry=raw_telemetry)

        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises(ValueError, tm_func, None)

        pus_17_telemetry = Service17Tm.unpack(raw_telemetry=pus_17_raw)
        self.assertTrue(pus_17_telemetry.service == 17)
        self.assertTrue(pus_17_telemetry.apid == 0xEF)
        self.assertTrue(pus_17_telemetry.subservice == 1)
        self.assertTrue(pus_17_telemetry.seq_count == 36)
        self.assertTrue(pus_17_telemetry.source_data == bytearray())
        self.assertTrue(pus_17_telemetry.pus_tm.valid)
        pus_17_telemetry.pus_tm.print_source_data(print_format=PrintFormats.HEX)
        pus_17_telemetry.pus_tm.print_full_packet_string(print_format=PrintFormats.HEX)
        # This string changes depending on system time, so its complicated to test its validity
        full_string = pus_17_telemetry.pus_tm.get_full_packet_string(
            print_format=PrintFormats.HEX
        )
        print(full_string)
        print(pus_17_telemetry)
        print(repr(pus_17_telemetry))
        self.assertTrue(pus_17_telemetry.pus_tm.packet_id.raw() == 0x8 << 8 | 0xEF)
