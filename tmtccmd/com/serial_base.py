import collections
import dataclasses
import enum
from enum import auto
import logging
import time
from typing import Optional

import serial


class SerialConfigIds(enum.Enum):

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


@dataclasses.dataclass
class SerialCfg:
    com_if_id: str
    serial_port: str
    baud_rate: int
    serial_timeout: float


class SerialComBase:
    def __init__(
        self,
        logger: logging.Logger,
        ser_cfg: SerialCfg,
        ser_com_type: SerialCommunicationType,
    ):
        self.logger = logger
        self.ser_cfg = ser_cfg
        self.ser_com_type = ser_com_type
        self.serial: Optional[serial.Serial] = None

    def open_port(self):
        try:
            self.serial = serial.Serial(
                port=self.ser_cfg.serial_port,
                baudrate=self.ser_cfg.baud_rate,
                timeout=self.ser_cfg.serial_timeout,
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

    @staticmethod
    def data_available_from_queue(timeout: float, reception_buffer: collections.deque):
        elapsed_time = 0
        start_time = time.time()
        sleep_time = timeout / 3.0
        if timeout > 0:
            while elapsed_time < timeout:
                if reception_buffer:
                    return reception_buffer.__len__()
                elapsed_time = time.time() - start_time
                time.sleep(sleep_time)
        if reception_buffer:
            return reception_buffer.__len__()
        return 0
