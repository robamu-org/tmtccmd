"""Base class for implementation of PUS Service 2 handling.
"""
from __future__ import annotations

from typing import Optional

import deprecation

from spacepackets.ccsds.time import CcsdsTimeProvider
from spacepackets.ecss.tm import CdsShortTimestamp, PusTelemetry

from tmtccmd import __version__
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase


class Service2Tm(PusTmInfoBase, PusTmBase):
    @deprecation.deprecated(
        deprecated_in="v4.0.0a1",
        current_version=__version__,
        details="use a custom wrapper type instead",
    )
    def __init__(
        self,
        subservice: int,
        time: Optional[CdsShortTimestamp] = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        pus_tm = PusTelemetry(
            service=2,
            subservice=subservice,
            time_provider=time,
            seq_count=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        PusTmBase.__init__(self, pus_tm=pus_tm)
        self.set_packet_info("Raw Commanding Reply")

    @classmethod
    def __empty(cls) -> Service2Tm:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls, raw_telemetry: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> Service2Tm:
        service_2_tm = cls.__empty()
        service_2_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, time_reader=time_reader
        )
        return service_2_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
