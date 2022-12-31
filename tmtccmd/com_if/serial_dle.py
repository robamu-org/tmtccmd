import threading
import time
from collections import deque
from typing import Optional

import serial
from dle_encoder import DleEncoder, STX_CHAR, ETX_CHAR, DleErrorCodes

from tmtccmd import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase
from tmtccmd.tm import TelemetryListT

LOGGER = get_console_logger()

# TODO: Maybe this should be configurable
DLE_MAX_FRAME_LENGTH = 4096


class SerialComDleComIF(SerialComBase, ComInterface):
    def __init__(
        self,
        com_if_id: str,
        com_port: str,
        baud_rate: int,
        serial_timeout: float,
    ):
        super().__init__(LOGGER, com_if_id, com_port, baud_rate, serial_timeout)
        self.encoder = DleEncoder()
        self.reception_thread = None
        self.reception_buffer = None
        self.dle_polling_active_event: Optional[threading.Event] = None
        # Set to default value.
        self.dle_queue_len = 10
        self.dle_max_frame = 256
        self.dle_timeout = 0.01
        self.dle_encode_cr = True

    def set_dle_settings(
        self,
        dle_queue_len: int,
        dle_max_frame: int,
        dle_timeout: float,
        encode_cr: bool = True,
    ):
        self.dle_queue_len = dle_queue_len
        self.dle_max_frame = dle_max_frame
        self.dle_timeout = dle_timeout
        self.dle_encode_cr = encode_cr

    def get_id(self) -> str:
        return self.com_if_id

    def initialize(self, args: any = None) -> any:
        self.reception_buffer = deque(maxlen=self.dle_queue_len)
        self.dle_polling_active_event = threading.Event()

    def open(self, args: any = None) -> None:
        super().open_port()
        self.dle_polling_active_event.set()
        self.reception_thread = threading.Thread(
            target=self.poll_dle_packets, daemon=True
        )
        self.reception_thread.start()

    def poll_dle_packets(self):
        while True and self.dle_polling_active_event.is_set():
            # Poll permanently, but it is possible to join this thread every 200 ms
            self.serial.timeout = 0.2
            data = bytearray()
            byte = self.serial.read()
            if len(byte) == 1 and byte[0] == STX_CHAR:
                data.append(byte[0])
                self.serial.timeout = 0.1
                bytes_rcvd = self.serial.read_until(
                    serial.to_bytes([ETX_CHAR]), DLE_MAX_FRAME_LENGTH
                )
                if bytes_rcvd[len(bytes_rcvd) - 1] == ETX_CHAR:
                    data.extend(bytes_rcvd)
                    self.reception_buffer.appendleft(data)
            elif len(byte) >= 1:
                data.append(byte[0])
                data.extend(self.serial.read(self.serial.inWaiting()))
                # It is assumed that all packets are DLE encoded, so throw it away for now.
                LOGGER.info(f"Non DLE-Encoded data with length {len(data) + 1} found..")

    def is_open(self) -> bool:
        return super().is_port_open()

    def close(self, args: any = None) -> None:
        self.dle_polling_active_event.clear()
        self.reception_thread.join(0.4)
        super().close_port()

    def send(self, data: bytes):
        encoded_data = self.encoder.encode(source_packet=data, add_stx_etx=True)
        self.serial.write(encoded_data)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        while self.reception_buffer:
            data = self.reception_buffer.pop()
            dle_retval, decoded_packet, read_len = self.encoder.decode(
                source_packet=data
            )
            if dle_retval == DleErrorCodes.OK:
                packet_list.append(decoded_packet)
            else:
                LOGGER.warning("DLE decoder error!")
        return packet_list

    def data_available(self, timeout: float, parameters: any) -> int:
        elapsed_time = 0
        start_time = time.time()
        sleep_time = timeout / 3.0
        if timeout > 0:
            while elapsed_time < timeout:
                if self.reception_buffer:
                    return self.reception_buffer.__len__()
                elapsed_time = time.time() - start_time
                time.sleep(sleep_time)
        if self.reception_buffer:
            return self.reception_buffer.__len__()
        return 0
