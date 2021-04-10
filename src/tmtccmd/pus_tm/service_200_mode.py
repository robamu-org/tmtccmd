"""
@brief  Base class for Service 200 mode commanding reply handling.
"""
import struct

from tmtccmd.ecss.tm import PusTelemetry


class Service200TM(PusTelemetry):
    def __init__(self, byte_array):
        super().__init__(byte_array)
        self.is_cant_reach_mode_reply = False
        self.is_mode_reply = False
        self.specify_packet_info("Mode Reply")
        self.object_id = struct.unpack('>I', self._tm_data[0:4])[0]
        if self.get_subservice() == 7:
            self.append_packet_info(": Can't reach mode")
            self.is_cant_reach_mode_reply = True
            self.returnValue = self._tm_data[4] << 8 | self._tm_data[5]
        elif self.get_subservice() == 6 or self.get_subservice() == 8:
            self.is_mode_reply = True
            if self.get_subservice() == 8:
                self.append_packet_info(": Wrong Mode")
            elif self.get_subservice() == 6:
                self.append_packet_info(": Mode reached")
            self.mode = struct.unpack('>I', self._tm_data[4:8])[0]
            self.submode = self._tm_data[8]

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self.object_id))
        if self.is_cant_reach_mode_reply:
            content_list.append(hex(self.returnValue))
        elif self.is_mode_reply:
            if self.mode == 1:
                mode_string = "ON"
            elif self.mode == 2:
                mode_string = "NORMAL"
            elif self.mode == 3:
                mode_string = "RAW"
            elif self.mode == 0:
                mode_string = "OFF"
            else:
                mode_string = f"UNKNOWN ({self.mode})"
            content_list.append(mode_string)
            content_list.append(str(self.submode))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        if self.is_cant_reach_mode_reply:
            header_list.append("Return Value")
        elif self.is_mode_reply:
            header_list.append("Mode")
            header_list.append("Submode")
