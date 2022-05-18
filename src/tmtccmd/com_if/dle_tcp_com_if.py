"""DLE over TCP Communication Interface Implementation
"""

# TODO WIP untested

from collections import deque
import socket
import threading

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.logging import get_console_logger
from dle_encoder import DleEncoder, STX_CHAR, ETX_CHAR, DleErrorCodes
from tmtccmd.tm.definitions import TelemetryListT


LOGGER = get_console_logger()


class DleTcpComIF(CommunicationInterface):
    def __init__(
        self,
        com_if_key: str,
        port: int,
        host: str
    ):
        super().__init__(com_if_key=com_if_key)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._port = port
        self._host = host

        self.encoder = DleEncoder()

        self.receive_queue = deque()

        self.receive_data = bytearray()

        self.reception_thread = threading.Thread(
            target=self.poll_dle_packets, daemon=True
        )

        self.dle_polling_active_event = threading.Event()

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        self.client_socket.connect((self._host, self._port))
        self.dle_polling_active_event.set()
        self.reception_thread.start()

    def close(self, args: any = None) -> None:
        self.dle_polling_active_event.clear()
        # TODO this will probably raise an exception, but for now, I can live with that
        # will probably be fixed when reconnecting is implemented
        self.client_socket.close()

    def send(self, data: bytes):
        encoded_data = self.encoder.encode(source_packet=data, add_stx_etx=True)
        self.client_socket.sendall(encoded_data)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        while self.receive_queue:
            packet_list.append(self.receive_queue.pop())
        return packet_list

    def data_available(self, timeout: float, parameters: any) -> int:
        return len(self.receive_queue)

    def poll_dle_packets(self):
        # Todo handle disconnect and reconnect properly
        while True and self.dle_polling_active_event.is_set():

            bytes = self.client_socket.recv(4096)

            self.receive_data += bytes

            index = self.receive_data.find(STX_CHAR)

            # no STX, no need to continue
            if index == -1:
                continue

            self.receive_data = self.receive_data[index:]

            while True:
                retval, decoded_packet, decoded_bytes = self.encoder.decode(self.receive_data)

                if retval == DleErrorCodes.OK:
                    self.receive_queue.appendleft(decoded_packet)
                    self.receive_data = self.receive_data[decoded_bytes:]
                    continue

                if retval == DleErrorCodes.END_REACHED:
                    # wait until we get more data
                    break

                if retval == DleErrorCodes.DECODING_ERROR:
                    self.receive_data = self.receive_data[decoded_bytes:]
                    # if there is no STX, no need to try again
                    if not STX_CHAR in self.receive_data:
                        break