"""TCP communication interface"""

from __future__ import annotations

import logging
import queue
import socket
import time
import enum
import threading
import select
from collections import deque
from typing import Any, Optional, Sequence

from spacepackets.ccsds.spacepacket import (
    PacketId,
    parse_space_packets_from_deque,
)

from tmtccmd.com import ComInterface, SendError
from tmtccmd.com.tcpip_utils import EthAddr

_LOGGER = logging.getLogger(__name__)

TCP_RECV_WIRETAPPING_ENABLED = False
TCP_SEND_WIRETAPPING_ENABLED = False


class TcpCommunicationType(enum.Enum):
    """Parse for space packets in the TCP stream, using the space packet header."""

    SPACE_PACKETS = 0


class TcpSpacepacketsClient(ComInterface):
    """Communication interface for TCP communication. This particular interface expects
    raw space packets to be sent via TCP and uses a list of passed packet IDs to parse for them.
    """

    def __init__(
        self,
        com_if_id: str,
        space_packet_ids: Sequence[PacketId],
        inner_thread_delay: float,
        target_address: EthAddr,
        max_packets_stored: Optional[int] = None,
    ):
        """Initialize a communication interface to send and receive TMTC via TCP.

        :param com_if_id:
        :param space_packet_ids: Valid packet IDs for CCSDS space packets. Those will be used
            to parse for space packets inside the TCP stream.
        :param inner_thread_delay: Polling frequency of TCP thread in seconds.
        """
        self.com_if_id = com_if_id
        self.com_type = TcpCommunicationType.SPACE_PACKETS
        self.space_packet_ids = space_packet_ids
        self.__inner_thread_delay = inner_thread_delay
        self.target_address = target_address
        self.max_packets_stored = max_packets_stored
        self.__conn_lock = threading.Lock()
        self.__connected = False
        self.__tcp_socket = None
        self.__thread_kill_signal = threading.Event()
        # Separate thread to request TM packets periodically if no TCs are being sent
        self.__tcp_thread = None
        self.__tm_queue = queue.Queue()
        self.__tc_queue = queue.Queue()
        self.__analysis_queue = deque()
        self._tm_packet_list = []

    @property
    def id(self) -> str:
        return self.com_if_id

    def __del__(self):
        try:
            self.close()
        except IOError:
            _LOGGER.warning("Could not close TCP communication interface!")

    def initialize(self, args: Any = None):
        pass

    def open(self, args: Any = None):
        if self.is_open():
            return
        self.__thread_kill_signal.clear()
        try:
            self.__init_socket()
            self.__connect_socket()
        except IOError as e:
            _LOGGER.exception("Issues setting up the TCP socket")
            raise e
        if self.__tcp_thread is None:
            self.__tcp_thread = threading.Thread(target=self.__tcp_task)
            self.__tcp_thread.start()
            with self.__conn_lock:
                self.__connected = True

    def is_open(self) -> bool:
        with self.__conn_lock:
            return self.__connected

    def __init_socket(self):
        if self.__tcp_socket is None:
            self.__tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__tcp_socket.settimeout(2.0)

    def __connect_socket(self):
        assert self.__tcp_socket is not None
        try:
            self.__tcp_socket.connect(self.target_address.to_tuple)
        except socket.timeout as e:
            _LOGGER.warning(f"Could not connect to socket with address {self.target_address}: {e}")
        finally:
            self.__tcp_socket.settimeout(None)

    def close(self, args: Any = None) -> None:
        if not self.is_open():
            return
        self.__thread_kill_signal.set()
        if self.__tcp_thread is not None:
            self.__tcp_thread.join(self.__inner_thread_delay)
            with self.__conn_lock:
                self.__connected = False
        self.__tcp_socket = None

    def send(self, data: bytes | bytearray):
        self.__tc_queue.put(data)

    def receive(self, parameters: float = 0) -> list[bytes]:
        self.__tm_queue_to_packet_list()
        tm_packet_list = self._tm_packet_list
        self._tm_packet_list = []
        return tm_packet_list

    def __tm_queue_to_packet_list(self):
        while self.__tm_queue.qsize() > 0:
            self.__analysis_queue.append(self.__tm_queue.get())
        # TCP is stream based, so there might be broken packets or multiple packets in one recv
        # call. We parse the space packets contained in the stream here
        if self.com_type == TcpCommunicationType.SPACE_PACKETS and self.__analysis_queue:
            result = parse_space_packets_from_deque(
                analysis_queue=self.__analysis_queue,
                packet_ids=self.space_packet_ids,
            )
            for packet in result.tm_list:
                self._tm_packet_list.append(packet)
            flattened = bytearray()
            while self.__analysis_queue:
                flattened.extend(self.__analysis_queue.popleft())
            # Might be spammy, but I consider this a configuration error, and the user
            # should be notified about it.
            for skipped_range in result.skipped_ranges:
                _LOGGER.warning("skipped bytes in received TCP datastream:")
                print(flattened[skipped_range.start : skipped_range.stop])
                _LOGGER.warning("list of valid packet IDs might be incomplete")
            self.__analysis_queue.append(flattened[result.scanned_bytes :])
        else:
            while self.__analysis_queue:
                self._tm_packet_list.append(self.__analysis_queue.popleft())

    def __tcp_task(self):
        while True and not self.__thread_kill_signal.is_set():
            try:
                self.__tmtc_event_loop()
            except ConnectionRefusedError:
                _LOGGER.warning("TCP connection attempt failed..")
            time.sleep(self.__inner_thread_delay)

    def __tmtc_event_loop(self):
        assert self.__tcp_socket is not None
        try:
            while True:
                outputs = []
                queue_size = self.__tc_queue.qsize()
                if queue_size > 0:
                    outputs.append(self.__tcp_socket)
                (readable, writable, _) = select.select(
                    [self.__tcp_socket], outputs, [], self.__inner_thread_delay
                )
                if self.__thread_kill_signal.is_set():
                    self.__tcp_socket.close()
                    break
                if queue_size > 0 and writable and writable[0]:
                    self.__tc_handling(queue_size)
                if readable and readable[0]:
                    self.__tm_handling()
        except KeyboardInterrupt:
            _LOGGER.info("Keyboard interrupt, shutting down TCP task")
            self.__force_shutdown()
        except ConnectionResetError:
            self.__force_shutdown()
            _LOGGER.exception("ConnectionResetError. TCP server might not be up")

    def __tc_handling(self, queue_size: int):
        try:
            self.__tcp_socket.sendto(self.__tc_queue.get(), self.target_address.to_tuple)
            queue_size -= 1
        except BrokenPipeError as e:
            raise SendError(f"{e}", e)
        except ConnectionRefusedError or OSError as e:
            self.__force_shutdown()
            raise SendError(f"TCP connection attempt failed with exception: {e}", e)

    def __tm_handling(self):
        bytes_recvd = self.__tcp_socket.recv(4096)
        if bytes_recvd == b"":
            self.__force_shutdown()
            _LOGGER.info("TCP server has been closed")
            return
        if (
            self.max_packets_stored is not None
            and self.__tm_queue.qsize() >= self.max_packets_stored
        ):
            _LOGGER.warning("Number of packets in TCP queue too large. Overwriting old packets..")
            self.__tm_queue.get()
            # TODO: If segments are received but the receiver is unable to parse packets
            #       properly, it might make sense to have a timeout which then also
            #       logs that there might be an issue reading packets
        self.__tm_queue.put(bytes(bytes_recvd))

    def data_available(self, timeout: float = 0, parameters: Any = 0) -> int:
        self.__tm_queue_to_packet_list()
        return len(self._tm_packet_list)

    def __force_shutdown(self):
        assert self.__tcp_socket is not None
        self.__tcp_socket.close()
        with self.__conn_lock:
            self.__connected = False
