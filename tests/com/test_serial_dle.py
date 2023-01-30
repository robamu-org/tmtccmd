import os
import sys
import time
import unittest
from typing import Optional
from unittest import TestCase

from tmtccmd.com.serial_base import SerialCfg
from tmtccmd.com.serial_dle import SerialDleComIF


@unittest.skipIf(sys.platform.startswith("win"), "pty only works on POSIX systems")
class TestSerialDleInterface(TestCase):
    _DLE_IF: Optional[SerialDleComIF] = None
    _PTY_MASTER: Optional[int] = None

    # The ComIF will spawn a separate receiver thread. Therefore, I'd like to have one
    # instance for all the tests. This is done by using the class setup and teardown methods.
    @classmethod
    def setUpClass(cls) -> None:
        import pty

        cls._PTY_MASTER, slave = pty.openpty()
        sname = os.ttyname(slave)
        ser_cfg = SerialCfg(
            com_if_id="pseudo_ser_dle",
            serial_port=sname,
            baud_rate=9600,
            serial_timeout=1.0,
        )
        cls._DLE_IF = SerialDleComIF(ser_cfg, None)
        cls._DLE_IF.open()
        cls._DLE_IF.initialize()

    def setUp(self) -> None:
        from dle_encoder.dle_encoder import DleEncoder

        self.encoder = DleEncoder()

    def test_state(self):
        self.assertTrue(self._DLE_IF.is_open())
        self.assertEqual(self._DLE_IF.data_available(0), 0)
        self.assertEqual(self._DLE_IF.id, "pseudo_ser_dle")

    def test_send(self):
        test_data = bytes([0x01, 0x02, 0x03])
        encoded_len = len(self.encoder.encode(test_data))
        self._DLE_IF.send(test_data)
        encoded_packet = os.read(self._PTY_MASTER, encoded_len)
        (errors, test_data_read_back, len_read) = self.encoder.decode(encoded_packet)
        self.assertEqual(test_data_read_back, test_data)

    def test_recv(self):
        test_data = bytes([0x02, 0x03, 0x04])
        encoded_test_data = self.encoder.encode(test_data)
        os.write(self._PTY_MASTER, encoded_test_data)
        # Give the receiver thread some time to do its work.
        time.sleep(0.1)
        self.assertEqual(self._DLE_IF.data_available(0), 1)
        packet_list = self._DLE_IF.receive()
        self.assertEqual(len(packet_list), 1)
        # Received data should be decoded now
        self.assertEqual(packet_list[0], test_data)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._DLE_IF.close()
