"""
@brief  Base class for Service 8 (Functional Commanding) Telemetry handling.
"""
import struct

from tmtccmd.pus_tm.base import PusTelemetry
from tmtccmd.core.object_id_manager import get_key_from_raw_object_id
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.core.definitions import CoreObjectIds

logger = get_logger()


class Service8TM(PusTelemetry):
    def __init__(self, byte_array):
        super().__init__(byte_array)
        self.source_object_id = 0
        self.object_id_key = CoreObjectIds.INVALID
        self.source_action_id = 0
        self.custom_data = bytearray()
        self.custom_data_header = []
        self.custom_data_content = []
        if self.get_subservice() == 130:
            self.specify_packet_info("Functional Data Reply")
            self.source_object_id = struct.unpack('!I', self.get_tm_data()[0:4])[0]
            self.object_id_key = get_key_from_raw_object_id(self.get_tm_data()[0:4])
            if self.object_id_key == CoreObjectIds.INVALID:
                logger.warning("Service8TM: Unknown object ID")
            self.source_action_id = struct.unpack('!I', self.get_tm_data()[4:8])[0]
            self.custom_data = self.get_tm_data()[8:]
        else:
            self.specify_packet_info("Functional Commanding Reply")
        try:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            self.custom_data_header, self.custom_data_content = \
                hook_obj.handle_servce_8_telemetry(
                    object_id=self.object_id_key, action_id=self.source_action_id,
                    custom_data=self.custom_data
                )
        except ImportError:
            logger.warning("Service 8 user data hook not supplied!")

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self.source_object_id))
        content_list.append(self.source_action_id)
        return

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        header_list.append("Action ID")
