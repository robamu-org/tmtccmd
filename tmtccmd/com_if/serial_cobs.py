from tmtccmd.com_if import ComInterface
from tmtccmd.com_if.serial_base import SerialComBase
from tmtccmd.tm import TelemetryListT


class SerialCobsComIF(SerialComBase, ComInterface):
    def __init__(self):
        pass

    def get_id(self) -> str:
        pass

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
