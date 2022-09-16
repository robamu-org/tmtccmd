"""TCP communication interface"""
import socket
import time
import enum
import threading
import select
from collections import deque
from typing import Optional, Tuple

from spacepackets.ccsds.spacepacket import parse_space_packets

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.tm import TelemetryListT
from tmtccmd.com_if.tcpip_utils import EthAddr
from tmtccmd.util.conf_util import acquire_timeout

LOGGER = get_console_logger()

TCP_RECV_WIRETAPPING_ENABLED = False
TCP_SEND_WIRETAPPING_ENABLED = False


class TcpCommunicationType(enum.Enum):
    """Parse for space packets in the TCP stream, using the space packet header"""

    SPACE_PACKETS = 0


class TcpComIF(ComInterface):
    """Communication interface for TCP communication.

    TODO: This class should not be tied to space packet IDs. Instead, let the parsing be done
          by an upper layer. Also, do we really need an extra thread here? Using select like
          with the UDP ComIF should be sufficient..
    """

    DEFAULT_LOCK_TIMEOUT = 0.4
    TM_LOOP_DELAY = 0.2

    def __init__(
        self,
        com_if_id: str,
        com_type: TcpCommunicationType,
        space_packet_ids: Tuple[int],
        tm_polling_freqency: float,
        target_address: EthAddr,
        max_recv_size: int,
        max_packets_stored: int = 50,
    ):
        """Initialize a communication interface to send and receive TMTC via TCP
        :param com_if_id:
        :param com_type:                Communication Type. By default, it is assumed that
                                        space packets are sent via TCP
        :param space_packet_ids:        16 bit packet header for space packet headers. Used to
                                        detect the start of PUS packets
        :param tm_polling_freqency:     Polling frequency in seconds
        """
        super().__init__(com_if_id=com_if_id)
        self.com_type = com_type
        self.space_packet_ids = space_packet_ids
        self.tm_polling_frequency = tm_polling_freqency
        self.target_address = target_address
        self.max_recv_size = max_recv_size
        self.max_packets_stored = max_packets_stored
        self.connected = False

        self.__tcp_socket: Optional[socket.socket] = None
        self.__last_connection_time = 0
        self.__tm_thread_kill_signal = threading.Event()
        # Separate thread to request TM packets periodically if no TCs are being sent
        self.__tcp_conn_thread: Optional[threading.Thread] = threading.Thread(
            target=self.__tcp_tm_client, daemon=True
        )
        self.__tm_queue = deque()
        self.__analysis_queue = deque()
        # Only allow one connection to OBSW at a time for now by using this lock
        # self.__socket_lock = threading.Lock()
        self.__queue_lock = threading.Lock()

    def __del__(self):
        try:
            self.close()
        except IOError:
            LOGGER.warning("Could not close TCP communication interface!")

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None):
        self.__tm_thread_kill_signal.clear()
        try:
            self.set_up_socket()
        except IOError as e:
            LOGGER.exception("Issues setting up the TCP socket")
            raise e
        self.set_up_tcp_thread()
        self.__tcp_conn_thread.start()

    def is_open(self) -> bool:
        return self.connected

    def set_up_socket(self):
        if self.__tcp_socket is None:
            self.__tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.__tcp_socket.settimeout(2.0)
                self.__tcp_socket.connect(self.target_address.to_tuple)
                self.connected = True
            except socket.timeout as e:
                LOGGER.warning(
                    f"Could not connect to socket with address {self.target_address}: {e}"
                )
            finally:
                self.__tcp_socket.settimeout(None)

    def set_up_tcp_thread(self):
        # TODO: Do we really need a thread here? This could probably be implemented as a polled
        #       interface like UDP, using the select API
        if self.__tcp_conn_thread is None:
            self.__tcp_conn_thread = threading.Thread(
                target=self.__tcp_tm_client, daemon=True
            )

    def close(self, args: any = None) -> None:
        self.__tm_thread_kill_signal.set()
        if self.__tcp_conn_thread is not None:
            if self.__tcp_conn_thread.is_alive():
                self.__tcp_conn_thread.join(self.tm_polling_frequency)
            if self.connected:
                try:
                    self.__tcp_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    LOGGER.warning(
                        "TCP socket endpoint was already closed or not connected"
                    )
                self.__tcp_socket.close()
        self.__tcp_socket = None
        self.__tcp_conn_thread = None

    def send(self, data: bytearray):
        try:
            if not self.connected:
                self.set_up_socket()
            self.__tcp_socket.sendto(data, self.target_address.to_tuple)
        except BrokenPipeError:
            LOGGER.exception("Communication Interface setup might have failed")
        except ConnectionRefusedError or OSError:
            self.connected = False
            self.__tcp_socket.close()
            self.__tcp_socket = None
            LOGGER.warning("TCP connection attempt failed..")

    def receive(self, poll_timeout: float = 0) -> TelemetryListT:
        tm_packet_list = []
        with acquire_timeout(
            self.__queue_lock, timeout=self.DEFAULT_LOCK_TIMEOUT
        ) as acquired:
            if not acquired:
                LOGGER.warning("Acquiring queue lock failed!")
            while self.__tm_queue:
                self.__analysis_queue.appendleft(self.__tm_queue.pop())
        # TCP is stream based, so there might be broken packets or multiple packets in one recv
        # call. We parse the space packets contained in the stream here
        if self.com_type == TcpCommunicationType.SPACE_PACKETS:
            tm_packet_list = parse_space_packets(
                analysis_queue=self.__analysis_queue, packet_ids=self.space_packet_ids
            )
        else:
            while self.__analysis_queue:
                tm_packet_list.append(self.__analysis_queue.pop())
        return tm_packet_list

    def __tcp_tm_client(self):
        while True and not self.__tm_thread_kill_signal.is_set():
            if self.connected:
                try:
                    self.__receive_tm_packets()
                except ConnectionRefusedError:
                    LOGGER.warning("TCP connection attempt failed..")
            time.sleep(self.TM_LOOP_DELAY)

    def __receive_tm_packets(self):
        try:
            ready = select.select([self.__tcp_socket], [], [], 0)
            if ready[0]:
                bytes_recvd = self.__tcp_socket.recv(self.max_recv_size)
                if bytes_recvd == b"":
                    self.__close_tcp_socket()
                    LOGGER.info("TCP server has been closed")
                    return
                else:
                    self.connected = True
                with acquire_timeout(
                    self.__queue_lock, timeout=self.DEFAULT_LOCK_TIMEOUT
                ) as acquired:
                    if not acquired:
                        LOGGER.warning("Acquiring queue lock failed!")
                    if self.__tm_queue.__len__() >= self.max_packets_stored:
                        LOGGER.warning(
                            "Number of packets in TCP queue too large. "
                            "Overwriting old packets.."
                        )
                        self.__tm_queue.pop()
                        # TODO: If segments are received but the receiver is unable to parse packets
                        #       properly, it might make sense to have a timeout which then also
                        #       logs that there might be an issue reading packets
                    self.__tm_queue.appendleft(bytes(bytes_recvd))
        except ConnectionResetError:
            self.__close_tcp_socket()
            LOGGER.exception("ConnectionResetError. TCP server might not be up")

    def data_available(self, timeout: float = 0, parameters: any = 0) -> bool:
        if self.__tm_queue:
            return True
        else:
            return False

    def __close_tcp_socket(self):
        self.connected = False
        self.__tcp_socket.close()
        self.__tcp_socket = None
