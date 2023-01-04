import collections
import threading
from typing import Optional

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase, SerialCfg, SerialCommunicationType
from tmtccmd.tm import TelemetryListT
from cobs import cobs


LOGGER = get_console_logger()


class SerialCobsComIF(SerialComBase, ComInterface):
    """Serial communication interface which uses the `COBS protocol <https://pypi.org/project/cobs/>`_
    to encode and decode packets.

    This class will spin up a receiver thread on the :meth:`open` call to poll
    for COBS encoded packets.
    This means that the :meth:`close` call might block until the receiver thread has shut down.
    """

    def __init__(self, ser_cfg: SerialCfg):
        super().__init__(
            LOGGER, ser_cfg=ser_cfg, ser_com_type=SerialCommunicationType.COBS
        )
        self.polling_active_event = threading.Event()
        self.reception_thread: Optional[threading.Thread] = None
        self.reception_buffer = collections.deque()

    def get_id(self) -> str:
        return self.ser_cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        """Spins up a receiver thread to permanently check for new COBS encoded packets."""
        super().open_port()
        self.reception_thread = threading.Thread(
            target=self.poll_cobs_packets, daemon=True
        )
        self.reception_thread.start()

    def is_open(self) -> bool:
        return self.serial is not None

    def close(self, args: any = None) -> None:
        self.polling_active_event.clear()
        self.reception_thread.join(0.4)
        super().close_port()

    def send(self, data: bytes):
        encoded = bytearray([0])
        encoded.extend(cobs.encode(data))
        encoded.append(0)
        self.serial.write(encoded)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        while self.reception_buffer:
            data = self.reception_buffer.pop()
            try:
                packet_list.extend(cobs.decode(data))
            except cobs.DecodeError as e:
                LOGGER.warning(f"COBS decoding error {e}")
        return packet_list

    def data_available(self, timeout: float, parameters: any) -> int:
        return SerialComBase.data_available_from_queue(timeout, self.reception_buffer)

    def poll_cobs_packets(self):
        last_byte_was_zero = False
        while True and self.polling_active_event.is_set():
            # Poll permanently, but it is possible to join this thread every 200 ms
            self.serial.timeout = 0.2
            byte = self.serial.read()
            if byte[0] == 0:
                last_byte_was_zero = True
            else:
                if last_byte_was_zero:
                    self.serial.timeout = 0.1
                    possible_cobs_frame = self.serial.read_until(0)
                    self.reception_buffer.appendleft(possible_cobs_frame)
                else:
                    last_byte_was_zero = False
