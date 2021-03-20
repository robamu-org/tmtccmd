"""
@file   tmtcc_ethernet_com_if.py
@date   01.11.2019
@brief  Ethernet Communication Interface

@author R. Mueller
"""
import enum
import select
import socket
import struct
import sys
import threading
from typing import Tuple

from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface, PusTmListT
from tmtccmd.pus_tm.factory import PusTelemetryFactory
from tmtccmd.pus_tc.base import PusTcInfoT
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.core.definitions import ethernet_address_t

LOGGER = get_logger()


# pylint: disable=abstract-method
# pylint: disable=arguments-differ
# pylint: disable=too-many-arguments
class TcpIpUdpComIF(CommunicationInterface):
    """
    Communication interface for UDP communication.
    """
    def __init__(self, tmtc_printer: TmTcPrinter, tm_timeout: float, tc_timeout_factor: float,
                 send_address: ethernet_address_t, max_recv_size: int):
        super().__init__(tmtc_printer)
        self.tm_timeout = tm_timeout
        self.tc_timeout_factor = tc_timeout_factor
        self.udp_socket = None
        self.socket_address = send_address
        self.max_recv_size = max_recv_size

    def __del__(self):
        try:
            self.close()
        except IOError:
            LOGGER.warning("Could not close UDP communication interface!")

    def initialize(self) -> None:
        pass

    def open(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set non-blocking because we use select.
        self.udp_socket.setblocking(False)

    def close(self) -> None:
        if self.udp_socket is None:
            self.udp_socket.close()

    def send_data(self, data: bytearray):
        self.udp_socket.sendto(data, self.destination_address)

    def send_telecommand(self, tc_packet: bytearray, tc_packet_info: PusTcInfoT = None) -> None:
        if self.udp_socket is None:
            return
        self.udp_socket.sendto(tc_packet, self.socket_address)

    def data_available(self, timeout: float = 0) -> bool:
        if self.udp_socket is None:
            return False
        ready = select.select([self.udp_socket], [], [], timeout)
        if ready[0]:
            return True
        return False

    def poll_interface(self, poll_timeout: float = 0) -> Tuple[bool, PusTmListT]:
        if self.udp_socket is None:
            return False, []
        ready = self.data_available(poll_timeout)
        if ready:
            data, sender_addr = self.udp_socket.recvfrom(self.max_recv_size)
            tm_packet = PusTelemetryFactory.create(bytearray(data))
            if tm_packet is None:
                return False, []
            packet_list = [tm_packet]
            return True, packet_list
        return False, []

    def receive_telemetry(self, parameters: any = 0) -> PusTmListT:
        packet_list = []
        if self.udp_socket is None:
            return packet_list
        try:
            (packet_received, packet_list) = self.poll_interface()
        except ConnectionResetError:
            LOGGER.warning("Connection reset exception occured!")
        return packet_list

    def connect_to_board(self):
        """
        For UDP, this can be used to initiate communication.
        :return:
        """
        ping = bytearray([])
        self.send_telecommand(ping)
