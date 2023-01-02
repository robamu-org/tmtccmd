import dataclasses
import threading
from collections import deque
from typing import Optional

import serial
from dle_encoder import DleEncoder, STX_CHAR, ETX_CHAR, DleErrorCodes

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase, SerialCfg
from tmtccmd.tm import TelemetryListT

LOGGER = get_console_logger()


@dataclasses.dataclass
class DleCfg:
    dle_queue_len: Optional[int] = None
    dle_max_frame: Optional[int] = None
    encode_cr: bool = True


class SerialDleComIF(SerialComBase, ComInterface):
    """Serial communication interface which uses the `DLE protocol <https://pypi.org/project/dle-encoder/>`_
    to encode and decode packets.

    This class will spin up a receiver thread on the :meth:`open` call to poll for DLE encoded packets.
    This means that the :meth:`close` call might block until the receiver thread has shut down.
    """

    def __init__(self, ser_cfg: SerialCfg, dle_cfg: Optional[DleCfg]):
        super().__init__(LOGGER, ser_cfg=ser_cfg)
        self.encoder = DleEncoder()
        self.reception_thread = None
        self.reception_buffer = None
        self.dle_polling_active_event: Optional[threading.Event] = None
        self.dle_cfg = dle_cfg

    def get_id(self) -> str:
        return self.ser_cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        if self.dle_cfg and self.dle_cfg.dle_queue_len:
            self.reception_buffer = deque(maxlen=self.dle_cfg.dle_queue_len)
        else:
            self.reception_buffer = deque()
        self.dle_polling_active_event = threading.Event()

    def open(self, args: any = None) -> None:
        """Spins up a receiver thread to permanently check for new DLE encoded packets."""
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
                if self.dle_cfg and self.dle_cfg.dle_max_frame:
                    bytes_rcvd = self.serial.read_until(
                        serial.to_bytes([ETX_CHAR]), self.dle_cfg.dle_max_frame
                    )
                else:
                    bytes_rcvd = self.serial.read_until(serial.to_bytes([ETX_CHAR]))
                if bytes_rcvd[len(bytes_rcvd) - 1] == ETX_CHAR:
                    data.extend(bytes_rcvd)
                    # deque is thread-safe for appends and pops from and to the opposite side
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
        return SerialComBase.data_available_from_queue(timeout, self.reception_buffer)
