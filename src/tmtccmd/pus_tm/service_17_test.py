from tmtccmd.pus_tm.base import PusTelemetry


class Service17TM(PusTelemetry):
    def __init__(self, byte_array):
        super().__init__(byte_array)
        self.specify_packet_info("Test Reply")

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        return

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        return
