from tmtccmd.logging import get_console_logger
from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase
from tmtccmd.tm import TelemetryListT


LOGGER = get_console_logger()


class SerialCobsComIF(SerialComBase, ComInterface):
    def __init__(
        self,
        com_if_id: str,
        com_port: str,
        baud_rate: int,
        serial_timeout: float,
    ):
        super().__init__(
            LOGGER,
            com_if_id=com_if_id,
            com_port=com_port,
            baud_rate=baud_rate,
            serial_timeout=serial_timeout,
        )

    def get_id(self) -> str:
        return self.com_if_id

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        pass

    def is_open(self) -> bool:
        pass

    def close(self, args: any = None) -> None:
        pass

    def send(self, data: bytes):
        pass

    def receive(self, parameters: any = 0) -> TelemetryListT:
        pass

    def data_available(self, timeout: float, parameters: any) -> int:
        pass
