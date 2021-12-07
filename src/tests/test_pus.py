#!/usr/bin/env python3
from unittest import TestCase

from spacepackets.ccsds.spacepacket import get_space_packet_sequence_control
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.conf import get_pus_tm_version, PusVersion, set_default_tm_apid
from spacepackets.util import PrintFormats

from tmtccmd.pus.service_17_test import Service17TMExtended


class TestTelemetry(TestCase):
    def test_generic_pus_c(self):
        pus_17_telemetry = Service17TMExtended(
            subservice=1,
            ssc=36,
            time=CdsShortTimestamp.init_from_current_time(),
            apid=0xEF,
        )
        pus_17_raw = pus_17_telemetry.pack()

        pus_17_telemetry = None

        def tm_func(raw_telemetry: bytearray):
            return Service17TMExtended.unpack(raw_telemetry=raw_telemetry)

        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises(ValueError, tm_func, None)

        pus_17_telemetry = Service17TMExtended.unpack(raw_telemetry=pus_17_raw)
        self.assertTrue(get_pus_tm_version() == PusVersion.PUS_C)
        self.assertTrue(pus_17_telemetry.service == 17)
        self.assertTrue(pus_17_telemetry.apid == 0xEF)
        self.assertTrue(pus_17_telemetry.subservice == 1)
        self.assertTrue(pus_17_telemetry.ssc == 36)
        self.assertTrue(pus_17_telemetry.tm_data == bytearray())
        self.assertTrue(pus_17_telemetry.pus_tm.valid)
        self.assertTrue(pus_17_telemetry.get_custom_printout() == "")
        self.assertTrue(pus_17_telemetry.get_source_data_string() == "hex []")
        pus_17_telemetry.pus_tm.print_source_data(print_format=PrintFormats.HEX)
        pus_17_telemetry.pus_tm.print_full_packet_string(print_format=PrintFormats.HEX)
        # This string changes depending on system time, so its complicated to test its validity
        full_string = pus_17_telemetry.pus_tm.get_full_packet_string(
            print_format=PrintFormats.HEX
        )
        print(full_string)
        print(pus_17_telemetry)
        print(repr(pus_17_telemetry))
        self.assertTrue(pus_17_telemetry.pus_tm.packet_id == 0x8 << 8 | 0xEF)

    def test_list_functionality(self):
        pus_17_telecommand = Service17TMExtended(
            subservice=1, ssc=36, time=CdsShortTimestamp.init_from_current_time()
        )
        pus_17_raw = pus_17_telecommand.pack()
        pus_17_telemetry = Service17TMExtended.unpack(raw_telemetry=pus_17_raw)

        header_list = []
        content_list = []
        pus_17_telemetry.append_telemetry_column_headers(header_list=header_list)
        pus_17_telemetry.append_telemetry_content(content_list=content_list)

        self.assertTrue(header_list != [])
        self.assertTrue(content_list != [])
