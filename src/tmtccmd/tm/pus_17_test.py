from __future__ import annotations
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss import PusVersion, PusTelemetry
from spacepackets.ecss.pus_17_test import Service17TM
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase

from tmtccmd.pus.pus_17_test import Subservices


class Service17TMExtended(PusTmBase, PusTmInfoBase, Service17TM):
    def __init__(
        self,
        subservice: int,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        Service17TM.__init__(
            self,
            subservice=subservice,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=self.pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=self.pus_tm)
        if self.subservice == Subservices.TM_REPLY:
            self.set_packet_info("Ping Reply")

    @classmethod
    def __empty(cls) -> Service17TMExtended:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytes,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service17TMExtended:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        return service_17_tm
