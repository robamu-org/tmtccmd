"""TCP communication interface"""
import logging
import socket
import time
import enum
import threading
import select
from collections import deque
from typing import Optional, Sequence

from spacepackets.ccsds.spacepacket import parse_space_packets, PacketId

from tmtccmd.com import ComInterface, SendError
from tmtccmd.tm import TelemetryListT
from tmtccmd.com.tcpip_utils import EthAddr

_LOGGER = logging.getLogger(__name__)

TCP_RECV_WIRETAPPING_ENABLED = False
TCP_SEND_WIRETAPPING_ENABLED = False


class TcpCommunicationType(enum.Enum):
    """Parse for space packets in the TCP stream, using the space packet header."""

    SPACE_PACKETS = 0


class TcpSpacePacketsComIF(ComInterface):
    """Communication interface for TCP communication. This particular interface expects
    raw space packets to be sent via TCP and uses a list of passed packet IDs to parse for them.
    """

    def __init__(
        self,
        com_if_id: str,
        space_packet_ids: Sequence[PacketId],
        tm_polling_freqency: float,
        target_address: EthAddr,
        max_packets_stored: int = 50,
    ):
        """Initialize a communication interface to send and receive TMTC via TCP.

        :param com_if_id:
        :param space_packet_ids: Valid packet IDs for CCSDS space packets. Those will be used
            to parse for space packets inside the TCP stream.
        :param tm_polling_freqency: Polling frequency in seconds
        """
        self.com_if_id = com_if_id
        self.com_type = TcpCommunicationType.SPACE_PACKETS
        self.space_packet_ids = space_packet_ids
        self.tm_polling_frequency = tm_polling_freqency
        self.target_address = target_address
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
        self.tm_packet_list = []

    @property
    def id(self) -> str:
        return self.com_if_id

    def __del__(self):
        try:
            self.close()
        except IOError:
            _LOGGER.warning("Could not close TCP communication interface!")

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None):
        self.__tm_thread_kill_signal.clear()
        try:
            self.set_up_socket()
        except IOError as e:
            _LOGGER.exception("Issues setting up the TCP socket")
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
                _LOGGER.warning(
                    f"Could not connect to socket with address {self.target_address}: {e}"
                )
            finally:
                self.__tcp_socket.settimeout(None)

    def set_up_tcp_thread(self):
        if self.__tcp_conn_thread is None:
            self.__tcp_conn_thread = threading.Thread(
                target=self.__tcp_tm_client, daemon=True
            )

    def close(self, args: any = None) -> None:
        self.__tm_thread_kill_signal.set()
        socket_was_closed = False
        if self.__tcp_conn_thread is not None:
            if self.__tcp_conn_thread.is_alive():
                self.__tcp_conn_thread.join(self.tm_polling_frequency)
            if self.connected:
                try:
                    self.__tcp_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    _LOGGER.warning(
                        "TCP socket endpoint was already closed or not connected"
                    )
                self.__tcp_socket.close()
                socket_was_closed = True
        if self.__tcp_socket is not None and not socket_was_closed:
            self.__tcp_socket.close()
        self.__tcp_socket = None
        self.__tcp_conn_thread = None

    def send(self, data: bytes):
        try:
            if not self.connected:
                self.set_up_socket()
            self.__tcp_socket.sendto(data, self.target_address.to_tuple)
        except BrokenPipeError as e:
            raise SendError(f"{e}", e)
        except ConnectionRefusedError or OSError as e:
            self.connected = False
            self.__tcp_socket.close()
            self.__tcp_socket = None
            raise SendError(f"TCP connection attempt failed with exception: {e}", e)

    def receive(self, poll_timeout: float = 0) -> TelemetryListT:
        self.__tm_queue_to_packet_list()
        tm_packet_list = self.tm_packet_list
        self.tm_packet_list = []
        return tm_packet_list

    def __tm_queue_to_packet_list(self):
        while self.__tm_queue:
            self.__analysis_queue.appendleft(self.__tm_queue.pop())
        # TCP is stream based, so there might be broken packets or multiple packets in one recv
        # call. We parse the space packets contained in the stream here
        if self.com_type == TcpCommunicationType.SPACE_PACKETS:
            self.tm_packet_list.extend(
                parse_space_packets(
                    analysis_queue=self.__analysis_queue,
                    packet_ids=self.space_packet_ids,
                )
            )
        else:
            while self.__analysis_queue:
                self.tm_packet_list.append(self.__analysis_queue.pop())

    def __tcp_tm_client(self):
        while True and not self.__tm_thread_kill_signal.is_set():
            if self.connected:
                try:
                    self.__receive_tm_packets()
                except ConnectionRefusedError:
                    _LOGGER.warning("TCP connection attempt failed..")
            time.sleep(self.tm_polling_frequency)

    def __receive_tm_packets(self):
        try:
            ready = select.select([self.__tcp_socket], [], [], 0)
            if ready[0]:
                bytes_recvd = self.__tcp_socket.recv(4096)
                if bytes_recvd == b"":
                    self.__close_tcp_socket()
                    _LOGGER.info("TCP server has been closed")
                    return
                else:
                    self.connected = True
                if self.__tm_queue.__len__() >= self.max_packets_stored:
                    _LOGGER.warning(
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
            _LOGGER.exception("ConnectionResetError. TCP server might not be up")

    def data_available(self, timeout: float = 0, parameters: any = 0) -> int:
        self.__tm_queue_to_packet_list()
        return len(self.tm_packet_list)

    def __close_tcp_socket(self):
        self.connected = False
        self.__tcp_socket.close()
        self.__tcp_socket = None
