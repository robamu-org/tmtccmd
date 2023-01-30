import select
import socket
from unittest import TestCase

from tmtccmd.com.tcpip_utils import EthAddr
from tmtccmd.com.udp import UdpComIF


LOCALHOST = "127.0.0.1"


class TestUdpIf(TestCase):
    def setUp(self) -> None:
        self.udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = (LOCALHOST, 7777)
        self.udp_server.bind(self.addr)
        self.udp_client = UdpComIF("udp", send_address=EthAddr.from_tuple(self.addr))
        self.udp_client.initialize()

    def test_basic(self):
        self.assertEqual(self.udp_client.id, "udp")
        self._open()

    def test_send(self):
        self._open()
        self._simple_send(bytes([0, 1, 2, 3]))

    def test_recv(self):
        self._open()
        data = bytes([0, 1, 2, 3])
        sender_addr = self._simple_send(data)
        self.udp_server.sendto(data, sender_addr)
        self.assertTrue(self.udp_client.data_available())
        data_recv = self.udp_client.receive()
        self.assertTrue(data_recv, data)

    def _simple_send(self, data: bytes) -> any:
        self.udp_client.send(data)
        ready = select.select([self.udp_server], [], [], 0.1)
        self.assertTrue(ready[0])
        data_recv, sender_addr = self.udp_server.recvfrom(4096)
        self.assertEqual(data, data_recv)
        return sender_addr

    def _open(self):
        self.udp_client.open()
        self.assertTrue(self.udp_client.is_open())

    def tearDown(self) -> None:
        self.udp_client.close()
        self.udp_server.close()
