import enum
import logging
from typing import Optional

import serial


class SerialConfigIds(enum.Enum):
    from enum import auto

    SERIAL_PORT = auto()
    SERIAL_BAUD_RATE = auto()
    SERIAL_TIMEOUT = auto()
    SERIAL_COMM_TYPE = auto()
    SERIAL_FRAME_SIZE = auto()
    SERIAL_DLE_QUEUE_LEN = auto()
    SERIAL_DLE_MAX_FRAME_SIZE = auto()


class SerialCommunicationType(enum.Enum):
    """
    Right now, two serial communication methods are supported. One uses frames with a fixed size
    containing PUS packets and the other uses a simple ASCII based transport layer called DLE.
    If DLE is used, it is expected that the sender side encoded the packets with the DLE
    protocol. Any packets sent will also be encoded.
    """

    COBS = 0
    FIXED_FRAME_BASED = 1
    DLE_ENCODING = 2


class SerialComBase:
    def __init__(
        self,
        logger: logging.Logger,
        com_if_id: str,
        com_port: str,
        baud_rate: int,
        serial_timeout: float,
        ser_com_type: SerialCommunicationType,
    ):
        self.logger = logger
        self.com_if_id = com_if_id
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_timeout = serial_timeout
        self.ser_com_type = ser_com_type
        self.serial: Optional[serial.Serial] = None

    def open_port(self):
        try:
            self.serial = serial.Serial(
                port=self.com_port, baudrate=self.baud_rate, timeout=self.serial_timeout
            )
        except serial.SerialException:
            self.logger.error("Serial Port opening failure!")
            raise IOError

    def close_port(self):
        try:
            self.serial.close()
            self.serial = None
        except serial.SerialException:
            logging.warning("SERIAL Port could not be closed!")

    def is_port_open(self) -> bool:
        return self.serial is not None
