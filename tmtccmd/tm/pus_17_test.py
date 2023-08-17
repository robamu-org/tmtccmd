from __future__ import annotations

import deprecation

from tmtccmd.version import get_version
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss import PusVersion, PusTelemetry
from spacepackets.ecss.pus_17_test import Service17Tm
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase

from tmtccmd.pus.s17_test import Subservice


class Service17TmExtended(PusTmBase, PusTmInfoBase, Service17Tm):
    @deprecation.deprecated(
        deprecated_in="v3.0.0rc2",
        current_version=get_version(),
        details="Use Service17Tm from the spacepackets package instead",
    )
    def __init__(
        self,
        subservice: int,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        Service17Tm.__init__(
            self,
            subservice=subservice,
            time_provider=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=self.pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=self.pus_tm)
        self.__set_internal_fields()

    @classmethod
    def __empty(cls) -> Service17TmExtended:
        return cls(subservice=0)

    def __set_internal_fields(self):
        if self.subservice == Subservice.TM_REPLY:
            self.set_packet_info("Ping Reply")

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytes,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service17TmExtended:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(
            data=raw_telemetry, time_reader=CdsShortTimestamp.empty()
        )
        service_17_tm.__set_internal_fields()
        return service_17_tm
