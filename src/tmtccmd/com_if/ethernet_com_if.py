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
from typing import Tuple

from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.com_if.com_interface_base import CommunicationInterface, PusTmListT
from tmtccmd.pus_tm.factory import PusTelemetryFactory
from tmtccmd.pus_tc.base import PusTcInfoT
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.core.definitions import ethernet_address_t

LOGGER = get_logger()


class EthernetConfigIds(enum.Enum):
    from enum import auto
    SEND_ADDRESS = auto()
    RECV_ADDRESS = auto()


# pylint: disable=abstract-method
# pylint: disable=arguments-differ
# pylint: disable=too-many-arguments
class EthernetComIF(CommunicationInterface):
    """
    Communication interface for UDP communication.
    """

    def send_data(self, data: bytearray):
        self.udp_socket.sendto(data, self.destination_address)

    def __init__(self, tmtc_printer: TmTcPrinter, tm_timeout: float, tc_timeout_factor: float,
                 receive_address: ethernet_address_t, send_address: ethernet_address_t):
        super().__init__(tmtc_printer)
        self.tm_timeout = tm_timeout
        self.tc_timeout_factor = tc_timeout_factor
        self.udp_socket = None
        self.receive_address = receive_address
        self.destination_address = send_address
        self.valid = True

    def __del__(self):
        try:
            self.close()
        except IOError:
            LOGGER.warning("Could not close UDP communication interface!")

    def initialize(self) -> None:
        pass

    def open(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_up_socket(self.receive_address)

    def close(self) -> None:
        self.udp_socket.close()

    def send_telecommand(self, tc_packet: bytearray, tc_packet_info: PusTcInfoT = None) -> None:
        if self.udp_socket is None:
            return
        self.udp_socket.sendto(tc_packet, self.destination_address)

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
            data = self.udp_socket.recvfrom(1024)[0]
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

    def set_up_socket(self, receive_address: ethernet_address_t):
        (recv_address, recv_port) = receive_address
        """
        Sets up the sockets for the UDP communication.
        :return:
        """
        try:
            if recv_address == socket.inet_ntoa(struct.pack('!L', socket.INADDR_ANY)):
                recv_printout = "all interfaces (INADDR_ANY)"
            elif recv_address == socket.inet_ntoa(struct.pack('!L', socket.INADDR_LOOPBACK)):
                recv_printout = "localhost (INADDR_LOOPBACK)"
            else:
                recv_printout = receive_address[0]
            LOGGER.info(f"Binding UDP socket to {recv_printout} and port {recv_port}")
            self.udp_socket.bind(receive_address)
            self.udp_socket.setblocking(False)
        except OSError:
            print("Socket already set-up.")
        except TypeError as error:
            print(error)
            print("Invalid Receive Address.")
            sys.exit()

    def connect_to_board(self):
        """
        For UDP, this can be used to initiate communication.
        :return:
        """
        ping = bytearray([])
        self.send_telecommand(ping)
