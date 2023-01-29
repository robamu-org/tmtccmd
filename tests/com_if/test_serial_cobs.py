import os
from unittest import TestCase
from tmtccmd.com.serial_cobs import SerialCobsComIF
import pty
from serial import Serial


class TestSerialCobsInterface(TestCase):
    def setUp(self) -> None:
        self.master, self.slave = pty.openpty()
        sname = os.ttyname(self.slave)
        # mname = os.ttyname(self.master)
        self.pseudo_dev = Serial(sname)
        # self.pseudo_master = Serial(mname)

    def test(self):
        # self.pseudo_master.write("hello\n".encode())
        self.pseudo_dev.write("hello\n".encode())
        # byte = self.pseudo_dev.read()
        # byte = self.pseudo_master.read()
        # print(byte)
        byte = os.read(self.master, 1)
        print(byte)
        os.write(self.master, "mello\n".encode())
        byte_back = self.pseudo_dev.read()
        print(byte_back)

    def tearDown(self) -> None:
        self.pseudo_dev.close()
