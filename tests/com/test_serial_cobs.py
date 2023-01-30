import os
import sys
import time
import unittest
from typing import Optional
from unittest import TestCase

from tmtccmd.com.serial_base import SerialCfg
from tmtccmd.com.serial_cobs import SerialCobsComIF


@unittest.skipIf(sys.platform.startswith("win"), "pty only works on POSIX systems")
class TestSerialCobsInterface(TestCase):
    _COBS_IF: Optional[SerialCobsComIF] = None
    _PTY_MASTER: Optional[int] = None

    # The ComIF will spawn a separate receiver thread. Therefore, I'd like to have one
    # instance for all the tests. This is done by using the class setup and teardown methods.
    @classmethod
    def setUpClass(cls) -> None:
        import pty

        cls._PTY_MASTER, slave = pty.openpty()
        sname = os.ttyname(slave)
        ser_cfg = SerialCfg(
            com_if_id="pseudo_ser_cobs",
            serial_port=sname,
            baud_rate=9600,
            serial_timeout=1.0,
        )
        cls._COBS_IF = SerialCobsComIF(ser_cfg)
        cls._COBS_IF.open()
        cls._COBS_IF.initialize()

    def setUp(self) -> None:
        pass

    def test_state(self):
        self.assertTrue(self._COBS_IF.is_open())
        self.assertEqual(self._COBS_IF.data_available(0), 0)
        self.assertEqual(self._COBS_IF.id, "pseudo_ser_cobs")

    def test_send(self):
        from cobs import cobs

        test_data = bytes([0x01, 0x02, 0x03])
        encoded_len = len(cobs.encode(test_data))
        self._COBS_IF.send(test_data)
        encoded_packet = os.read(self._PTY_MASTER, encoded_len + 2)
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
        os.write(self._PTY_MASTER, full_data_to_send)
        # Give the receiver thread some time to do its work.
        time.sleep(0.1)
        self.assertEqual(self._COBS_IF.data_available(0), 1)
        packet_list = self._COBS_IF.receive()
        self.assertEqual(len(packet_list), 1)
        # Received data should be decoded now
        self.assertEqual(packet_list[0], test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._COBS_IF.close()
