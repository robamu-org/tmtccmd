from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus.service_17 import Srv17Subservices


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


class Service17TmPacked(PusTelemetryCreator):
    """
    Class representation for Service 1 TM creation.
    """
    def __init__(self, subservice: int, ssc: int = 0, tc_packet_id: int = 0, tc_ssc: int = 0):
        super().__init__(service=17, subservice=Srv17Subservices.PING_REPLY, ssc=ssc, source_data=source_data)

    def pack(self) -> bytearray:
        return super().pack()