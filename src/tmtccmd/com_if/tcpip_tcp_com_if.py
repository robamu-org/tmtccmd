"""
:file:      tcpip_tcp_com_if.py
:date:      13.05.2021
:brief:     TCP communication interface
:author:    R. Mueller
"""
import socket
import time
import threading
from collections import deque
from typing import Union

from tmtccmd.utility.logger import get_console_logger
from tmtccmd.config.definitions import CoreModeList
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.tm.definitions import TelemetryListT
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.config.definitions import EthernetAddressT

LOGGER = get_console_logger()

TCP_RECV_WIRETAPPING_ENABLED = False
TCP_SEND_WIRETAPPING_ENABLED = False


# pylint: disable=abstract-method
# pylint: disable=arguments-differ
# pylint: disable=too-many-arguments
class TcpIpTcpComIF(CommunicationInterface):
    """
    Communication interface for UDP communication.
    """
    def __init__(
            self, com_if_key: str, tm_polling_freqency: float, tm_timeout: float, tc_timeout_factor: float,
            send_address: EthernetAddressT, max_recv_size: int, max_packets_stored: int = 50,
            tmtc_printer: Union[None, TmTcPrinter] = None, init_mode: int = CoreModeList.LISTENER_MODE):
        """
        Initialize a communication interface to send and receive UDP datagrams.
        :param com_if_key:
        :param tm_polling_freqency:     Polling frequency in seconds
        :param tm_timeout:              Timeout in seconds
        :param tmtc_printer: Printer instance, can be passed optionally to allow packet debugging
        """
        super().__init__(com_if_key=com_if_key, tmtc_printer=tmtc_printer)
        self.tm_timeout = tm_timeout
        self.tc_timeout_factor = tc_timeout_factor
        self.tm_polling_frequency = tm_polling_freqency
        self.send_address = send_address
        self.max_recv_size = max_recv_size
        self.max_packets_stored = max_packets_stored
        self.init_mode = init_mode

        self.__last_connection_time = 0
        self.__tm_thread_kill_signal = threading.Event()
        # Separate thread to request TM packets periodically if no TCs are being sent
        self.__tcp_conn_thread = threading.Thread(target=self.__tcp_tm_client, daemon=True)
        self.__tm_queue = deque()
        # Only allow one connection to OBSW at a time for now by using this lock
        self.__socket_lock = threading.Lock()

    def __del__(self):
        try:
            self.close()
        except IOError:
            LOGGER.warning("Could not close UDP communication interface!")

    def initialize(self, args: any = None) -> any:
        self.__tm_thread_kill_signal.clear()

    def open(self, args: any = None):
        self.__tcp_conn_thread.start()

    def close(self, args: any = None) -> None:
        self.__tm_thread_kill_signal.set()
        self.__tcp_conn_thread.join(self.tm_polling_frequency)

    def send(self, data: bytearray):
        try:
            with self.__socket_lock:
                tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_socket.connect(self.send_address)
                tcp_socket.sendto(data, self.send_address)
                tcp_socket.shutdown(socket.SHUT_WR)
                self.__receive_tm_packets(tcp_socket)
                self.__last_connection_time = time.time()
                tcp_socket.close()
        except ConnectionRefusedError:
            LOGGER.warning("TCP connection attempt failed..")

    def receive(self, poll_timeout: float = 0) -> TelemetryListT:
        tm_packet_list = []
        while self.__tm_queue:
            tm_packet_list.append(self.__tm_queue.pop())
        return tm_packet_list

    def __tcp_tm_client(self):
        while True and not self.__tm_thread_kill_signal.is_set():
            if time.time() - self.__last_connection_time >= self.tm_polling_frequency:
                try:
                    with self.__socket_lock:
                        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        tcp_socket.connect(self.send_address)
                        tcp_socket.shutdown(socket.SHUT_WR)
                        self.__receive_tm_packets(tcp_socket=tcp_socket)
                        self.__last_connection_time = time.time()
                except ConnectionRefusedError:
                    LOGGER.warning("TCP connection attempt failed..")
                    self.__last_connection_time = time.time()
            time.sleep(self.tm_polling_frequency / 2.0)

    def __receive_tm_packets(self, tcp_socket: socket.socket):
        while True:
            bytes_recvd = tcp_socket.recv(self.max_recv_size)
            if len(bytes_recvd) > 0:
                if self.__tm_queue.__len__() >= self.max_packets_stored:
                    LOGGER.warning("Number of packets in TCP queue too large. Overwriting old packets..")
                    self.__tm_queue.pop()
                self.__tm_queue.appendleft(bytearray(bytes_recvd))
            elif bytes_recvd is None or len(bytes_recvd) == 0:
                break

    def data_available(self, timeout: float = 0, parameters: any = 0) -> bool:
        if self.__tm_queue:
            return True
        else:
            return False
