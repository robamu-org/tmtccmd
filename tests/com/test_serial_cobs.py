import os
from unittest import TestCase

from cobs import cobs
from tmtccmd.com.serial_base import SerialCfg
from tmtccmd.com.serial_cobs import SerialCobsComIF
import pty
from serial import Serial


class TestSerialCobsInterface(TestCase):
    def setUp(self) -> None:
        self.master, self.slave = pty.openpty()
        sname = os.ttyname(self.slave)
        # mname = os.ttyname(self.master)
        self.pseudo_dev = Serial(sname)
        self.ser_cfg = SerialCfg(
            com_if_id="pseudo_ser_cobs",
            serial_port=sname,
            baud_rate=9600,
            serial_timeout=1.0,
        )
        self.cobs_if = SerialCobsComIF(self.ser_cfg)
        self.cobs_if.open()
        # self.pseudo_master = Serial(mname)

    def test_send(self):
        test_data = bytes([0x01, 0x02, 0x03])
        encoded_len = len(cobs.encode(test_data))
        self.cobs_if.send(test_data)
        encoded_packet = os.read(self.master, encoded_len + 2)
        test_data_read_back = cobs.decode(encoded_packet[1:-1])
        self.assertEqual(test_data_read_back, test_data)

    def tearDown(self) -> None:
        self.cobs_if.close()
