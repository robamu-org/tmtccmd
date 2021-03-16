# -*- coding: utf-8 -*-
"""
Program: tmtcc_tm_service5.py
Date: 30.12.2019
Description: Deserialize PUS Event Report
Author: R. Mueller
"""

from tmtccmd.pus_tm.base import PusTelemetry, TmDictionaryKeys
from tmtccmd.pus_tm.factory import PusTmInfoT
import struct


class Service5TM(PusTelemetry):
    def __init__(self, byte_array):
        super().__init__(byte_array)
        self.specify_packet_info("Event")
        if self.get_subservice() == 1:
            self.append_packet_info(" Info")
        elif self.get_subservice() == 2:
            self.append_packet_info(" Error Low Severity")
        elif self.get_subservice() == 3:
            self.append_packet_info(" Error Med Severity")
        elif self.get_subservice() == 4:
            self.append_packet_info(" Error High Severity")
        self.eventId = struct.unpack('>H', self._tm_data[0:2])[0]
        self.objectId = struct.unpack('>I', self._tm_data[2:6])[0]
        self.param1 = struct.unpack('>I', self._tm_data[6:10])[0]
        self.param2 = struct.unpack('>I', self._tm_data[10:14])[0]

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(self.eventId))
        content_list.append(hex(self.objectId))
        content_list.append(str(hex(self.param1)) + ", " + str(self.param1))
        content_list.append(str(hex(self.param2)) + ", " + str(self.param2))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Event ID")
        header_list.append("Reporter ID")
        header_list.append("Parameter 1")
        header_list.append("Parameter 2")

    def pack_tm_information(self) -> PusTmInfoT:
        tm_information = super().pack_tm_information()
        add_information = {
            TmDictionaryKeys.REPORTER_ID: self.objectId,
            TmDictionaryKeys.EVENT_ID: self.eventId,
            TmDictionaryKeys.EVENT_PARAM_1: self.param1,
            TmDictionaryKeys.EVENT_PARAM_2: self.param2
        }
        tm_information.update(add_information)
        return tm_information
