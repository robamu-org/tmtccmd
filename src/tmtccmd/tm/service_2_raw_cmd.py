"""
@brief  Base class for implementation of PUS Service 2 handling.
"""
from tmtccmd.ecss.tm import PusTelemetry


class Service2TM(PusTelemetry):
    def __init__(self, byte_array: bytearray):
        super().__init__(byte_array)
        self.specify_packet_info("Raw Commanding Reply")

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        return

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        return
