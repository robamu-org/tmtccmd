import select
import socket
import time
from typing import Any
from unittest import TestCase

from spacepackets import PacketType
from spacepackets.ccsds import PacketId
from spacepackets.ecss import PusTelecommand, PusTelemetry
from tmtccmd.com.tcp import TcpComIF, TcpCommunicationType
from tmtccmd.com.tcpip_utils import EthAddr


LOCALHOST = "127.0.0.1"
START_ADDR = 7777


class TestTcpIf(TestCase):
    def setUp(self) -> None:
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.addr = (LOCALHOST, 7777)
        self.tcp_server.bind(self.addr)
        self.tcp_server.listen()
        self.expected_packet_id = PacketId(
            apid=0x22, sec_header_flag=True, ptype=PacketType.TM
        )
        self.ping_cmd = PusTelecommand(service=17, subservice=1, apid=0x22)
        self.ping_reply = PusTelemetry(
            service=17, subservice=2, apid=0x22, time_provider=None
        )
        self.tcp_client = TcpComIF(
            "tcp",
            com_type=TcpCommunicationType.SPACE_PACKETS,
            space_packet_ids=(self.expected_packet_id,),
            target_address=EthAddr.from_tuple(self.addr),
            tm_polling_freqency=0.05,
        )
        self.tcp_client.initialize()

    def test_monolithic(self):
        self._open()
        self._test_basic()
        self._test_send()
        self._test_recv()

    def _test_basic(self):
        self.assertEqual(self.tcp_client.get_id(), "tcp")

    def _test_send(self):
        self._simple_send_only(bytes([0, 1, 2, 3]))

    def _test_recv(self):
        self._send_back_ping_reply(self.ping_cmd.pack())
        time.sleep(0.1)
        packets_read_back = self.tcp_client.receive()
        self.assertEqual(packets_read_back, 1)

    def _simple_send_only(self, data: bytes):
        (sock, _, _) = self._simple_send(data)
        sock.close()

    def _simple_send(self, data: bytes) -> (socket.socket, bytes, Any):
        self.tcp_client.send(data)
        ready = select.select([self.tcp_server], [], [], 0.2)
        self.assertTrue(ready[0])
        (conn_socket, conn_addr) = self.tcp_server.accept()
        data_recv, sender_addr = conn_socket.recvfrom(4096)
        self.assertEqual(data, data_recv)
        return conn_socket, data_recv, sender_addr

    def _send_back_ping_reply(self, data: bytes):
        conn_socket, data_recv, sender_addr = self._simple_send(data)
        conn_socket.sendto(self.ping_reply.pack(), sender_addr)
        conn_socket.close()
        return sender_addr

    def _open(self):
        self.tcp_client.open()
        self.assertTrue(self.tcp_client.is_open())

    def tearDown(self) -> None:
        self.tcp_server.close()
        self.tcp_client.close()
