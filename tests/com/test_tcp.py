import socket
from unittest import TestCase

from tmtccmd.com.tcp import TcpComIF, TcpCommunicationType
from tmtccmd.com.tcpip_utils import EthAddr


LOCALHOST = "127.0.0.1"


class TestTcpIf(TestCase):
    def setUp(self) -> None:
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (LOCALHOST, 7777)
        self.tcp_server.bind(self.addr)
        self.tcp_server.listen()
        self.sp_ids = (0x22,)
        self.tcp_client = TcpComIF(
            "tcp",
            com_type=TcpCommunicationType.SPACE_PACKETS,
            space_packet_ids=self.sp_ids,
            target_address=EthAddr.from_tuple(self.addr),
            tm_polling_freqency=0.05,
        )
        self.tcp_client.initialize()

    def test_basic(self):
        self.assertEqual(self.tcp_client.get_id(), "tcp")
        self._open()

    def _open(self):
        self.tcp_client.open()
        self.assertTrue(self.tcp_client.is_open())
