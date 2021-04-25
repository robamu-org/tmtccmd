#!/usr/bin/env python3
import unittest
from crcmod import crcmod
from unittest import TestCase

from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.ecss.tc import generate_crc, generate_packet_crc


class TestTelemetry(TestCase):
    def test_tm(self):
        self.assertTrue(True)


class TestTelecommand(TestCase):
    def test_tc(self):
        self.assertTrue(True)

    def test_crc_16(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc = crc_func(pus_17_telecommand.pack())
        self.assertTrue(crc == 0)

        test_data = bytearray([192, 23, 4, 82, 3, 6])
        data_with_crc = generate_crc(test_data)
        crc = crc_func(data_with_crc)
        self.assertTrue(crc == 0)

        packet_raw = pus_17_telecommand.pack()
        packet_raw[len(packet_raw) - 1] += 1
        self.assertTrue(crc_func(packet_raw) != 0)
        packet_raw = generate_packet_crc(packet_raw)
        self.assertTrue(crc_func(packet_raw) == 0)



if __name__ == '__main__':
    unittest.main()
