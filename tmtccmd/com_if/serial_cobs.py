import collections
import threading
from typing import Optional

from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase, SerialArgs
from tmtccmd.tm import TelemetryListT
from cobs import cobs


LOGGER = get_console_logger()


class SerialCobsComIF(SerialComBase, ComInterface):
    def __init__(self, cfg: SerialArgs):
        super().__init__(LOGGER, cfg=cfg)
        self.polling_active_event: Optional[threading.Event] = None
        self.reception_thread: Optional[threading.Thread] = None
        self.reception_buffer: Optional[collections.deque] = None

    def get_id(self) -> str:
        return self.cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        super().open_port()
        self.reception_thread = threading.Thread(
            target=self.poll_cobs_packets, daemon=True
        )
        self.reception_thread.start()

    def is_open(self) -> bool:
        return self.serial is not None

    def close(self, args: any = None) -> None:
        pass

    def send(self, data: bytes):
        encoded = cobs.encode(data)
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
        pass

    def poll_cobs_packets(self):
        pass
