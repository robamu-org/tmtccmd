#!/usr/bin/env python3
from unittest import TestCase

from spacepackets.ccsds.spacepacket import get_space_packet_sequence_control
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.conf import get_pus_tm_version, PusVersion

from tmtccmd.tm.service_17_test import Service17TM


class TestTelemetry(TestCase):
    def test_space_packet_functions(self):
        psc = get_space_packet_sequence_control(sequence_flags=0b111, source_sequence_count=42)
        self.assertTrue(psc & 0xc000 == 0xc000)

    def test_generic_pus_c(self):
        pus_17_telemetry = Service17TM(
            subservice_id=1, ssc=36, time=CdsShortTimestamp.init_from_current_time()
        )
        pus_17_raw = pus_17_telemetry.pack()

        pus_17_telemetry = None

        def tm_func(raw_telemetry: bytearray):
            return Service17TM.unpack(raw_telemetry=raw_telemetry)

        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises(ValueError, tm_func, None)

        pus_17_telemetry = Service17TM.unpack(raw_telemetry=pus_17_raw)

        self.assertTrue(get_pus_tm_version() == PusVersion.PUS_C)
        self.assertTrue(pus_17_telemetry.get_service() == 17)
        self.assertTrue(pus_17_telemetry.get_apid() == 0xef)
        self.assertTrue(pus_17_telemetry.get_subservice() == 1)
        self.assertTrue(pus_17_telemetry.get_ssc() == 36)
        self.assertTrue(pus_17_telemetry.get_tm_data() == bytearray())
        self.assertTrue(pus_17_telemetry.pus_tm.is_valid())
        self.assertTrue(pus_17_telemetry.get_custom_printout() == "")
        self.assertTrue(pus_17_telemetry.return_source_data_string() == "[]")
        pus_17_telemetry.pus_tm.print_source_data()
        pus_17_telemetry.pus_tm.print_full_packet_string()
        # This string changes depending on system time, so its complicated to test its validity
        full_string = pus_17_telemetry.pus_tm.return_full_packet_string()
        print(full_string)
        print(pus_17_telemetry)
        print(repr(pus_17_telemetry))
        self.assertTrue(pus_17_telemetry.pus_tm.get_packet_id() == 0x8 << 8 | 0xef)

    def test_list_functionality(self):
        pus_17_telecommand = Service17TM(
            subservice_id=1, ssc=36, time=CdsShortTimestamp.init_from_current_time()
        )
        pus_17_raw = pus_17_telecommand.pack()
        pus_17_telemetry = Service17TM.unpack(raw_telemetry=pus_17_raw)

        header_list = []
        content_list = []
        pus_17_telemetry.append_telemetry_column_headers(header_list=header_list)
        pus_17_telemetry.append_telemetry_content(content_list=content_list)

        self.assertTrue(header_list != [])
        self.assertTrue(content_list != [])
