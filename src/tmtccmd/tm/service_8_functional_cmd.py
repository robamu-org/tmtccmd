"""Contains classes and functions to handle PUS Service 8 telemetry.
"""
import struct

from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class Service8TM(PusTelemetry):
    def __init__(self, raw_telemetry: bytearray, call_srv8_hook: bool = True):
        """This class can be used to deserialize service 8 packets.
        :param raw_telemetry:      Raw bytearray which will be deserialized
        :param call_srv8_hook:
        :raises ValueError: If the length of the passed bytearray is too short.
        """
        super().__init__(raw_telemetry=raw_telemetry)
        self._object_id_bytes = bytearray()
        self._object_id = 0
        self._action_id = 0
        self._custom_data = bytearray()
        if self.get_subservice() == 130:
            tm_data = self.get_tm_data()
            if len(tm_data) < 8:
                LOGGER.warning(f'Length of Service 8 TM data field {len(tm_data)} short than 8')
                raise ValueError
            self.specify_packet_info("Functional Data Reply")
            self._object_id_bytes = self.get_tm_data()[0:4]
            self._object_id = struct.unpack('!I', self._object_id_bytes)[0]
            self._action_id = struct.unpack('!I', self.get_tm_data()[4:8])[0]
            self._custom_data = self.get_tm_data()[8:]
        else:
            self.specify_packet_info("Unknown functional commanding reply")

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self._object_id))
        content_list.append(self._action_id)

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        header_list.append("Action ID")

    def get_source_object_id_as_bytes(self) -> bytes:
        return bytes(self._object_id_bytes)

    def get_source_object_id(self) -> int:
        return self._object_id

    def get_action_id(self) -> int:
        return self._action_id

    def get_custom_data(self) -> bytearray:
        return self._custom_data
