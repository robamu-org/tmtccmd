import logging
import time

import deprecation

from tmtccmd.version import get_version
from tmtccmd.com import ComInterface
from tmtccmd.com.serial_base import SerialComBase, SerialCfg
from tmtccmd.tm import TelemetryListT


# TODO: This should be configurable
SERIAL_FRAME_MAX_LENGTH = 4096


# TODO: Consider removing this? Sending binary data without some sort of transport layer
#       is not really the best approach..
@deprecation.deprecated(
    deprecated_in="4.0.0a0",
    current_version=get_version(),
    details="Please use a serial interface using a transport layer like SerialCobsComIF",
)
class SerialFixedFrameComIF(SerialComBase, ComInterface):
    def __init__(self, ser_cfg: SerialCfg):
        super().__init__(logging.getLogger(__name__), ser_cfg=ser_cfg)
        # Set to default value.
        self.serial_frame_size = SERIAL_FRAME_MAX_LENGTH

    def set_fixed_frame_settings(self, serial_frame_size: int):
        self.serial_frame_size = serial_frame_size

    @property
    def id(self) -> str:
        return self.ser_cfg.com_if_id

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        super().open_port()

    def is_open(self) -> bool:
        return super().is_port_open()

    def close(self, args: any = None) -> None:
        return super().close_port()

    def send(self, data: bytes):
        self.serial.write(data)

    def receive(self, parameters: any = 0) -> TelemetryListT:
        packet_list = []
        if self.data_available(0, None):
            data = self.serial.read(self.serial_frame_size)
            pus_data_list = poll_pus_packets_fixed_frames(bytearray(data))
            for pus_packet in pus_data_list:
                packet_list.append(pus_packet)
        return packet_list

    def data_available(self, timeout: float, parameters: any) -> int:
        sleep_time = timeout / 3.0
        return self.data_available_fixed_frame(timeout=timeout, sleep_time=sleep_time)

    def data_available_fixed_frame(self, timeout: float, sleep_time: float):
        if timeout > 0:
            start_time = time.time()
            elapsed_time = 0
            while elapsed_time < timeout:
                if self.serial.inWaiting() > 0:
                    return self.serial.inWaiting()
                elapsed_time = time.time() - start_time
                time.sleep(sleep_time)
        if self.serial.inWaiting() > 0:
            return self.serial.inWaiting()


def poll_pus_packets_fixed_frames(data: bytearray) -> list:
    pus_data_list = []
    if len(data) == 0:
        return pus_data_list

    payload_length = data[4] << 8 | data[5]
    packet_size = payload_length + 7
    if payload_length == 0:
        return []
    read_size = len(data)
    pus_data = data[0:packet_size]
    pus_data_list.append(pus_data)

    SerialFixedFrameComIF.read_multiple_packets(
        data, packet_size, read_size, pus_data_list
    )
    return pus_data_list


def read_multiple_packets(
    data: bytearray, start_index: int, frame_size: int, pus_data_list: list
):
    while start_index < frame_size:
        start_index = SerialFixedFrameComIF.parse_next_packets(
            data, start_index, frame_size, pus_data_list
        )


def parse_next_packets(
    data: bytearray, start_index: int, frame_size: int, pus_data_list: list
) -> int:
    next_payload_len = data[start_index + 4] << 8 | data[start_index + 5]
    if next_payload_len == 0:
        end_index = frame_size
        return end_index
    next_packet_size = next_payload_len + 7

    if next_packet_size > SERIAL_FRAME_MAX_LENGTH:
        logger = logging.getLogger(__name__)
        logger.error(
            "PUS Polling: Very large packet detected, packet splitting not implemented yet!"
        )
        logger.error("Detected Size: " + str(next_packet_size))
        end_index = frame_size
        return end_index

    end_index = start_index + next_packet_size
    pus_data = data[start_index:end_index]
    pus_data_list.append(pus_data)
    return end_index
