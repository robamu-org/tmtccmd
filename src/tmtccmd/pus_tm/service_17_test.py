from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.ecss.tm_creator import PusTelemetryCreator


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
    def __init__(self, subservice: int, ssc: int = 0, source_data: bytearray = bytearray()):
        super().__init__(service=17, subservice=subservice, ssc=ssc, source_data=source_data)

    def pack(self) -> bytearray:
        return super().pack()
