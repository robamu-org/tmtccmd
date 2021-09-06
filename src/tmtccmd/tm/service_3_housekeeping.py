# -*- coding: utf-8 -*-
"""PUS Service 3 components
"""
from __future__ import annotations
from abc import abstractmethod
import struct

from tmtccmd.pus import ObjectId
from tmtccmd.ecss.tm import PusTelemetry, PusTmInfoBase, PusTmBase, CdsShortTimestamp, PusVersion
from tmtccmd.tm import Service3Base
from tmtccmd.utility.logger import get_console_logger
from typing import Type, Tuple, List


LOGGER = get_console_logger()


class Service3TM(Service3Base, PusTmBase, PusTmInfoBase):
    """This class encapsulates the format of Service 3 telemetry
    This class was written to handle Service 3 telemetry coming from the on-board software
    based on the Flight Software Framework (FSFW). A custom class can be defined, but should then
    implement Service3Base.
    """
    # Minimal packet contains SID, which consists of object ID(4) and set ID(4)
    DEFAULT_MINIMAL_PACKET_SIZE = 8
    # Minimal structure report contains SID (8), reporting status(1), validity flag (1),
    # collection interval as float (4) and number of parameters(1)
    STRUCTURE_REPORT_FIXED_HEADER_SIZE = DEFAULT_MINIMAL_PACKET_SIZE + 7

    def __init__(
            self, subservice_id: int, time: CdsShortTimestamp, hk_data: bytearray,
            custom_hk_handling: bool = False, ssc: int = 0, apid: int = -1,
            minimum_reply_size: int = DEFAULT_MINIMAL_PACKET_SIZE,
            minimum_structure_report_header_size: int = STRUCTURE_REPORT_FIXED_HEADER_SIZE,
            packet_version: int = 0b000, pus_version: PusVersion = PusVersion.UNKNOWN,
            pus_tm_version: int = 0b0001, ack: int = 0b1111, secondary_header_flag: bool = True,
            space_time_ref: int = 0b0000, destination_id: int = 0
    ):
        """Service 3 packet class representation which can be built from a raw bytearray
        :param subservice_id:
        :param time:
        :param hk_data:
        :param custom_hk_handling:  Can be used if a custom HK format is used which does not
                                    use a 8 byte structure ID (SID).
        :param minimum_reply_size:
        :param minimum_structure_report_header_size:
        """
        Service3Base.__init__(self, object_id=0, custom_hk_handling=custom_hk_handling)
        source_data = bytearray()
        source_data.extend(struct.pack('!I', self.get_object_id().get_id()))
        source_data.extend(struct.pack('!I', self._set_id))
        if subservice_id == 25 or subservice_id == 26:
            source_data.extend(hk_data)
        pus_tm = PusTelemetry(
            service_id=3,
            subservice_id=subservice_id,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            pus_tm_version=pus_tm_version,
            ack=ack,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id
        )
        PusTmBase.__init__(self, pus_tm=pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        self.__init_without_base(
            instance=self, custom_hk_handling=custom_hk_handling,
            minimum_reply_size=minimum_reply_size,
            minimum_structure_report_header_size=minimum_structure_report_header_size,
            check_tm_data_size=False
        )

    @staticmethod
    def __init_without_base(
            instance: Service3TM, custom_hk_handling: bool,
            check_tm_data_size: bool,
            minimum_reply_size: int = DEFAULT_MINIMAL_PACKET_SIZE,
            minimum_structure_report_header_size: int = STRUCTURE_REPORT_FIXED_HEADER_SIZE
    ):
        instance.set_custom_hk_handling(custom_hk_handling=custom_hk_handling)
        if instance.has_custom_hk_handling():
            return
        tm_data = instance.get_tm_data()
        if len(tm_data) < 8:
            LOGGER.warning(
                f'Invalid Service 3 packet, is too short. Detected TM data length: {len(tm_data)}'
            )
            raise ValueError
        instance.min_hk_reply_size = minimum_reply_size
        instance.hk_structure_report_header_size = minimum_structure_report_header_size
        instance.get_object_id().set_from_bytes(obj_id_as_bytes=tm_data[0:4])
        instance._set_id = struct.unpack('!I', tm_data[4:8])[0]
        if instance.get_subservice() == 25 or instance.get_subservice() == 26:
            if len(tm_data) > 8:
                instance._param_length = len(tm_data[8:])
        instance.specify_packet_info("Housekeeping Packet")

    @classmethod
    def __empty(cls) -> Service3TM:
        return cls(
            subservice_id=-1,
            time=CdsShortTimestamp.init_from_current_time(),
            hk_data=bytearray()
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, custom_hk_handling: bool,
            pus_version: PusVersion = PusVersion.UNKNOWN,
    ) -> Service3TM:
        service_3_tm = cls.__empty()
        service_3_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        service_3_tm.__init_without_base(
            instance=service_3_tm, custom_hk_handling=custom_hk_handling,
            check_tm_data_size=True
        )
        return service_3_tm

    @abstractmethod
    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(self.get_object_id().as_string())
        content_list.append(hex(self._set_id))
        content_list.append(int(self._param_length))

    @abstractmethod
    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        header_list.append("Set ID")
        header_list.append("HK data size")

    def get_hk_definitions_list(self) -> Tuple[List, List]:
        tm_data = self.get_tm_data()
        if len(tm_data) < self.hk_structure_report_header_size:
            LOGGER.warning(
                f'Service3TM: handle_filling_definition_arrays: Invalid structure report '
                f'from {self.get_object_id().as_string()}, is shorter '
                f'than {self.hk_structure_report_header_size}'
            )
            return [], []
        definitions_header = [
            "Object ID", "Set ID", "Report Status", "Is valid", "Collection Interval (s)",
            "Number Of IDs"
        ]
        reporting_enabled = tm_data[8]
        set_valid = tm_data[9]
        collection_interval_seconds = struct.unpack('!f', tm_data[10:14])[0] / 1000.0
        num_params = tm_data[14]
        if len(tm_data) < self.hk_structure_report_header_size + num_params * 4:
            LOGGER.warning(
                f'Service3TM: handle_filling_definition_arrays: Invalid structure report '
                f'from {self.get_object_id().as_string()}, is shorter than '
                f'{self.hk_structure_report_header_size + num_params * 4}'
            )
            return [], []

        parameters = []
        counter = 1
        for array_index in range(
                self.hk_structure_report_header_size,
                self.hk_structure_report_header_size + 4 * num_params, 4
        ):
            parameter = struct.unpack('!I', tm_data[array_index:array_index + 4])[0]
            definitions_header.append("Pool ID " + str(counter))
            parameters.append(str(hex(parameter)))
            counter = counter + 1
        if reporting_enabled == 1:
            status_string = "On"
        else:
            status_string = "Off"
        if set_valid:
            valid_string = "Yes"
        else:
            valid_string = "No"
        definitions_content = [
            self.get_object_id().as_string(), self._set_id, status_string, valid_string,
            collection_interval_seconds, num_params
        ]
        definitions_content.extend(parameters)
        return definitions_header, definitions_content
