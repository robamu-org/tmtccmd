import collections
import threading
import time
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
        self.polling_active_event = threading.Event()
        self.reception_thread: Optional[threading.Thread] = None
        self.reception_buffer = collections.deque()

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
        self.polling_active_event.clear()
        self.reception_thread.join(0.4)
        super().close_port()

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
