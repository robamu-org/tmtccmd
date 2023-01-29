import os
import sys
import time
import unittest
from unittest import TestCase

from tmtccmd.com.serial_base import SerialCfg
from tmtccmd.com.serial_cobs import SerialCobsComIF


@unittest.skipIf(sys.platform.startswith("win"), "pty only works on POSIX systems")
class TestSerialCobsInterface(TestCase):
    def setUp(self) -> None:
        import pty
        self.master, self.slave = pty.openpty()
        sname = os.ttyname(self.slave)
        self.ser_cfg = SerialCfg(
            com_if_id="pseudo_ser_cobs",
            serial_port=sname,
            baud_rate=9600,
            serial_timeout=1.0,
        )
        self.cobs_if = SerialCobsComIF(self.ser_cfg)
        self.cobs_if.open()
        self.cobs_if.initialize()

    def test_state(self):
        self.assertTrue(self.cobs_if.is_open())
        self.assertEqual(self.cobs_if.data_available(0), 0)
        self.assertEqual(self.cobs_if.get_id(), "pseudo_ser_cobs")

    def test_send(self):
        from cobs import cobs
        test_data = bytes([0x01, 0x02, 0x03])
        encoded_len = len(cobs.encode(test_data))
        self.cobs_if.send(test_data)
        encoded_packet = os.read(self.master, encoded_len + 2)
        test_data_read_back = cobs.decode(encoded_packet[1:-1])
        self.assertEqual(test_data_read_back, test_data)

    def test_recv(self):
        from cobs import cobs
        test_data = bytes([0x02, 0x03, 0x04])
        encoded_test_data = cobs.encode(test_data)
        # Add packer delimiters.
        full_data_to_send = bytearray([0x00])
        full_data_to_send.extend(encoded_test_data)
        full_data_to_send.append(0)
        os.write(self.master, full_data_to_send)
        # Give the receiver thread some time to do its work.
        time.sleep(0.1)
        self.assertEqual(self.cobs_if.data_available(0), 1)
        packet_list = self.cobs_if.receive()
        self.assertEqual(len(packet_list), 1)
        # Received data should be decoded now
        self.assertEqual(packet_list[0], test_data)

    def tearDown(self) -> None:
        self.cobs_if.close()
