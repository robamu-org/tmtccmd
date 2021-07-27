# -*- coding: utf-8 -*-
"""Contains classes and functions to deserialize PUS Service 5 Telemetry
"""
import struct
from tmtccmd.pus.service_list import PusServices
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.ecss.tm_creator import PusTelemetryCreator
from tmtccmd.pus.service_5_event import Srv5Subservices, Severity
from tmtccmd.utility.logger import get_console_logger


LOGGER = get_console_logger()


class Service5TM(PusTelemetry):
    def __init__(self, byte_array: bytearray):
        """Deserialize a raw PUS Service 5 packet
        :param byte_array:      Raw bytearray to deserialize, containing the service 5 packet.
        :raises ValueError: If the length of the raw telemetry is too short
        """
        super().__init__(raw_telemetry=byte_array)
        if self.get_service() != 5:
            LOGGER.warning("This packet is not an event service packet!")

        self.specify_packet_info("Event")
        if self.get_subservice() == Srv5Subservices.INFO_EVENT:
            self.append_packet_info(" Info")
        elif self.get_subservice() == Srv5Subservices.LOW_SEVERITY_EVENT:
            self.append_packet_info(" Error Low Severity")
        elif self.get_subservice() == Srv5Subservices.MEDIUM_SEVERITY_EVENT:
            self.append_packet_info(" Error Med Severity")
        elif self.get_subservice() == Srv5Subservices.HIGH_SEVERITY_EVENT:
            self.append_packet_info(" Error High Severity")
        tm_data = self.get_tm_data()
        if len(tm_data) < 14:
            LOGGER.warning(f'Length of TM data field {len(tm_data)} shorter than expected 14 bytes')
            raise ValueError
        self._event_id = struct.unpack('>H', tm_data[0:2])[0]
        self._object_id_as_bytes = tm_data[2:6]
        self._object_id = struct.unpack('>I', self._object_id_as_bytes)[0]
        self._param_1 = struct.unpack('>I', tm_data[6:10])[0]
        self._param_2 = struct.unpack('>I', tm_data[10:14])[0]

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(self._event_id))
        content_list.append(hex(self._object_id))
        content_list.append(str(hex(self._param_1)) + ", " + str(self._param_1))
        content_list.append(str(hex(self._param_2)) + ", " + str(self._param_2))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Event ID")
        header_list.append("Reporter ID")
        header_list.append("Parameter 1")
        header_list.append("Parameter 2")

    def get_reporter_id_as_bytes(self) -> bytes:
        return self._object_id_as_bytes

    def get_reporter_id(self) -> int:
        return self._object_id

    def get_event_id(self):
        return self._event_id

    def get_param_1(self):
        return self._param_1

    def get_param_2(self):
        return self._param_2


class Service5TmPacked(PusTelemetryCreator):
    """
    Class representation for Service 5 TM creation.
    """
    def __init__(
            self, severity: Severity, event_id: int, object_id: bytearray = bytearray(),
            param_1: int = 0, param_2: int = 0, ssc: int = 0
    ):
        self.event_id = event_id
        self.object_id = object_id
        self.param_1 = param_1
        self.param_2 = param_2
        source_data = bytearray()
        source_data.extend(struct.pack('!H', self.event_id))
        source_data.extend(object_id)
        source_data.extend(struct.pack('!I', self.param_1))
        source_data.extend(struct.pack('!I', self.param_2))
        super().__init__(
            service=PusServices.SERVICE_5_EVENT, subservice=severity, ssc=ssc,
            source_data=source_data)

    def pack(self) -> bytearray:
        return super().pack()
