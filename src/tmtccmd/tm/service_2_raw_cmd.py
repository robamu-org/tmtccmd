"""Base class for implementation of PUS Service 2 handling.
"""
from __future__ import annotations
from tmtccmd.ecss.tm import PusTmInfoBase, PusTmBase, CdsShortTimestamp, PusVersion, PusTelemetry


class Service2TM(PusTmInfoBase, PusTmBase):
    def __init__(
            self, subservice_id: int, time: CdsShortTimestamp = None, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, packet_version: int = 0b000,
            pus_version: PusVersion = PusVersion.UNKNOWN, pus_tm_version: int = 0b0001,
            ack: int = 0b1111, secondary_header_flag: bool = True, space_time_ref: int = 0b0000,
            destination_id: int = 0
    ):
        pus_tm = PusTelemetry(
            service_id=2,
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
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        PusTmBase.__init__(self, pus_tm=pus_tm)
        self.specify_packet_info("Raw Commanding Reply")

    @classmethod
    def __empty(cls) -> Service2TM:
        return cls(
            subservice_id=0
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.UNKNOWN
    ) -> Service2TM:
        service_2_tm = cls.__empty()
        service_2_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        return service_2_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        return

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        return
