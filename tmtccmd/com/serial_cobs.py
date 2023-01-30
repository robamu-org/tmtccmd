import collections
import threading
from typing import Optional

from tmtccmd.logging import get_console_logger
from tmtccmd.com import ComInterface, ReceptionDecodeError
from tmtccmd.com.serial_base import SerialComBase, SerialCfg, SerialCommunicationType
from tmtccmd.tm import TelemetryListT
from cobs import cobs


LOGGER = get_console_logger()


class SerialCobsComIF(SerialComBase, ComInterface):
    """Serial communication interface which uses the
    `COBS protocol <https://pypi.org/project/cobs/>`_ to encode and decode packets.

    This class will spin up a receiver thread on the :meth:`open` call to poll
    for COBS encoded packets.
    This means that the :meth:`close` call might block until the receiver thread has shut down.
    """

    def __init__(self, ser_cfg: SerialCfg):
        super().__init__(
            LOGGER, ser_cfg=ser_cfg, ser_com_type=SerialCommunicationType.COBS
        )
        self.__polling_shutdown = threading.Event()
        self.__reception_thread: Optional[threading.Thread] = None
        self.__reception_buffer = collections.deque()

    @property
    def id(self) -> str:
        return self.ser_cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        """Spins up a receiver thread to permanently check for new COBS encoded packets."""
        super().open_port()
        self.__polling_shutdown.clear()
        self.__reception_thread = threading.Thread(
            target=self.__poll_cobs_packets, daemon=True
        )
        self.__reception_thread.start()

    def is_open(self) -> bool:
        return self.serial is not None

    def close(self, args: any = None) -> None:
        self.__polling_shutdown.set()
        self.__reception_thread.join(0.4)
        super().close_port()

    def send(self, data: bytes):
        encoded = bytearray([0])
        encoded.extend(cobs.encode(data))
        encoded.append(0)
        self.serial.write(encoded)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        while self.__reception_buffer:
            data = self.__reception_buffer.pop()
            try:
                packet_list.append(cobs.decode(data))
            except cobs.DecodeError as e:
                raise ReceptionDecodeError(f"COBS decoding error: {e}", e)
        return packet_list

    def data_available(self, timeout: float, parameters: any = 0) -> int:
        return SerialComBase.data_available_from_queue(timeout, self.__reception_buffer)

    def __poll_cobs_packets(self):
        last_byte_was_zero = False
        # Poll permanently, but it is possible to join this thread every 200 ms
        self.serial.timeout = 0.2
        while True:
            byte = self.serial.read()
            if len(byte) == 1:
                if byte[0] == 0:
                    last_byte_was_zero = True
                else:
                    if last_byte_was_zero:
                        self.serial.timeout = 0.1
                        possible_cobs_frame = bytearray(byte)
                        possible_cobs_frame.extend(self.serial.read_until(bytes([0])))
                        self.__reception_buffer.appendleft(possible_cobs_frame[:-1])
                        self.serial.timeout = 0.2
                        last_byte_was_zero = True
                    else:
                        broken_cobs_frame = self.serial.read_until(bytes([0]))
                        LOGGER.warning(
                            f"Discarding possibly broken COBS frame: "
                            f"{broken_cobs_frame.hex(sep=',')}"
                        )
                        last_byte_was_zero = True
            elif self.__polling_shutdown.is_set():
                break
