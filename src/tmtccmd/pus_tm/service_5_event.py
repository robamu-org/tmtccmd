# -*- coding: utf-8 -*-
"""
:file:      service_5_event.py
:date:      30.12.2019
:brief:     Deserialize PUS Event Report
:author:    R. Mueller
"""
import struct
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus.service_5_event import Srv5Subservices
from tmtccmd.core.object_id_manager import get_key_from_raw_object_id
from tmtccmd.utility.tmtcc_logger import get_logger


LOGGER = get_logger()

class Service5TM(PusTelemetry):
    def __init__(self, byte_array, call_srv5_hook: bool = True):
        super().__init__(byte_array)
        self.specify_packet_info("Event")
        if self.get_subservice() == Srv5Subservices.INFO_EVENT:
            self.append_packet_info(" Info")
        elif self.get_subservice() == Srv5Subservices.LOW_SEVERITY_EVENT:
            self.append_packet_info(" Error Low Severity")
        elif self.get_subservice() == Srv5Subservices.MEDIUM_SEVERITY_EVENT:
            self.append_packet_info(" Error Med Severity")
        elif self.get_subservice() == Srv5Subservices.HIGH_SEVERITY_EVENT:
            self.append_packet_info(" Error High Severity")
        self.event_id = struct.unpack('>H', self._tm_data[0:2])[0]
        self.object_id = struct.unpack('>I', self._tm_data[2:6])[0]
        self.object_id_key = get_key_from_raw_object_id(self.get_tm_data()[2:6])
        self.param_1 = struct.unpack('>I', self._tm_data[6:10])[0]
        self.param_2 = struct.unpack('>I', self._tm_data[10:14])[0]
        if call_srv5_hook:
            from tmtccmd.core.hook_base import TmTcHookBase
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            hook_obj.handle_service_8_telemetry()

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(self.event_id))
        content_list.append(hex(self.object_id))
        content_list.append(str(hex(self.param_1)) + ", " + str(self.param_1))
        content_list.append(str(hex(self.param_2)) + ", " + str(self.param_2))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Event ID")
        header_list.append("Reporter ID")
        header_list.append("Parameter 1")
        header_list.append("Parameter 2")

    def handle_service_5_event(self, object_id: int, event_id: int, param_1: int, param_2: int) -> str:
        try:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            self.custom_data_header, self.custom_data_content = \
                hook_obj.handle_service_5_event(
                    object_id=self.object_id_key, event_id=event_id, param_1=param_1, param_2=param_2
                )
        except ImportError:
            LOGGER.warning("Service 5 user data hook not supplied!")

    def get_reporter_id(self):
        return self.object_id

    def get_event_id(self):
        return self.event_id

    def get_param_1(self):
        return self.param_1

    def get_param_2(self):
        return self.param_2
