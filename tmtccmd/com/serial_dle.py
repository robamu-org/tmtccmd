import dataclasses
import logging
import threading
from collections import deque
from typing import Optional

import serial
from dle_encoder import DleEncoder, STX_CHAR, ETX_CHAR, DleErrorCodes

from tmtccmd.com import ComInterface
from tmtccmd.com.serial_base import SerialComBase, SerialCfg, SerialCommunicationType
from tmtccmd.tm import TelemetryListT


@dataclasses.dataclass
class DleCfg:
    dle_queue_len: Optional[int] = None
    dle_max_frame: Optional[int] = None
    encode_cr: bool = True


class SerialDleComIF(SerialComBase, ComInterface):
    """Serial communication interface which uses the
    `DLE protocol <https://pypi.org/project/dle-encoder/>`_ to encode and decode packets.

    This class will spin up a receiver thread on the :meth:`open` call to poll for DLE encoded
    packets. This means that the :meth:`close` call might block until the receiver thread has shut
    down.
    """

    def __init__(self, ser_cfg: SerialCfg, dle_cfg: Optional[DleCfg]):
        super().__init__(
            logging.getLogger(__name__),
            ser_cfg=ser_cfg,
            ser_com_type=SerialCommunicationType.DLE_ENCODING,
        )
        self.dle_cfg = dle_cfg
        self.__encoder = DleEncoder()
        self.__reception_thread = None
        self.__reception_buffer = deque()
        self.__polling_shutdown: Optional[threading.Event] = threading.Event()

    @property
    def id(self) -> str:
        return self.ser_cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        if self.dle_cfg and self.dle_cfg.dle_queue_len:
            self.__reception_buffer = deque(maxlen=self.dle_cfg.dle_queue_len)

    def open(self, args: any = None) -> None:
        """Spins up a receiver thread to permanently check for new DLE encoded packets."""
        super().open_port()
        self.__polling_shutdown.clear()
        self.__reception_thread = threading.Thread(
            target=self.__poll_dle_packets, daemon=True
        )
        self.__reception_thread.start()

    def __poll_dle_packets(self):
        # Poll permanently, but it is possible to join this thread every 200 ms
        self.serial.timeout = 0.2
        data = bytearray()
        while True:
            byte = self.serial.read()
            if len(byte) == 1:
                if byte[0] == STX_CHAR:
                    data.append(byte[0])
                    self.serial.timeout = 0.1
                    if self.dle_cfg and self.dle_cfg.dle_max_frame:
                        bytes_rcvd = self.serial.read_until(
                            serial.to_bytes([ETX_CHAR]), self.dle_cfg.dle_max_frame
                        )
                    else:
                        bytes_rcvd = self.serial.read_until(serial.to_bytes([ETX_CHAR]))
                    self.serial.timeout = 0.2
                    if bytes_rcvd[len(bytes_rcvd) - 1] == ETX_CHAR:
                        data.extend(bytes_rcvd)
                        # deque is thread-safe for appends and pops from and to the opposite side
                        self.__reception_buffer.appendleft(data)
                data = bytearray()
            elif self.__polling_shutdown.is_set():
                break

    def is_open(self) -> bool:
        return super().is_port_open()

    def close(self, args: any = None) -> None:
        self.__polling_shutdown.set()
        self.__reception_thread.join(0.4)
        super().close_port()

    def send(self, data: bytes):
        encoded_data = self.__encoder.encode(source_packet=data, add_stx_etx=True)
        self.serial.write(encoded_data)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        while self.__reception_buffer:
            data = self.__reception_buffer.pop()
            dle_retval, decoded_packet, read_len = self.__encoder.decode(
                source_packet=data
            )
            if dle_retval == DleErrorCodes.OK:
                packet_list.append(decoded_packet)
            else:
                self.logger.warning("DLE decoder error!")
        return packet_list

    def data_available(self, timeout: float, parameters: any = 0) -> int:
        return SerialComBase.data_available_from_queue(timeout, self.__reception_buffer)
