from __future__ import annotations

from typing import Optional

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.time import CdsShortTimestamp, CcsdsTimeProvider
from spacepackets.ecss import (
    Ptc,
    PusTelemetry,
)
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import AbstractPusTm

from tmtccmd.pus.s20_fsfw_param import (
    CustomSubservice,
)
from tmtccmd.pus.s20_fsfw_param_defs import ParameterId, Parameter


class Service20ParamDumpWrapper:
    def __init__(self, param_tm: Service20FsfwTm):
        self.param_tm = param_tm
        if self.param_tm.subservice != CustomSubservice.TM_DUMP_REPLY:
            raise ValueError(f"subservice is not {CustomSubservice.TM_DUMP_REPLY}")

    @property
    def base_tm(self) -> PusTelemetry:
        return self.param_tm.pus_tm

    def get_param(self) -> Parameter:
        """Tries to build a :py:class:`Parameter` from the own raw telemetry data.

        :raises ValueError: Telemetry source data too short.
        """
        if len(self.param_tm.source_data) < 12:
            raise ValueError("source data too short to hold parameter")
        param_id = ParameterId.unpack(self.param_tm.source_data[4:8])
        try:
            ptc = Ptc(self.param_tm.source_data[8])
        except TypeError:
            raise ValueError(f"unknown PTC {self.param_tm.source_data[8]}")
        pfc = self.param_tm.source_data[9]
        rows = self.param_tm.source_data[10]
        columns = self.param_tm.source_data[11]
        param_data = self.param_tm.source_data[12:]
        return Parameter(
            object_id=self.param_tm.source_data[0:4],
            param_id=param_id,
            ptc=Ptc(ptc),
            pfc=pfc,
            rows=rows,
            columns=columns,
            param_raw=param_data,
        )


class Service20FsfwTm(AbstractPusTm):
    def __init__(
        self,
        subservice: int,
        source_data: bytes,
        time_provider: Optional[CcsdsTimeProvider],
        apid: int = 0,
    ):
        self.pus_tm = PusTelemetry(
            service=PusService.S20_PARAMETER,
            subservice=subservice,
            source_data=source_data,
            time_provider=time_provider,
            apid=apid,
        )

    @staticmethod
    def __common_checks(tm: PusTelemetry):
        if tm.service != 20:
            raise ValueError("service ID is not 20")
        if len(tm.source_data) < 4:
            raise ValueError(
                "source data must include object ID (4 bytes) as minimal data"
            )

    @classmethod
    def unpack(
        cls, raw_telemetry: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> Service20FsfwTm:
        instance = cls.empty()
        instance.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, time_reader=time_reader
        )
        Service20FsfwTm.__common_checks(instance.pus_tm)
        return instance

    @classmethod
    def from_tm(cls, tm: PusTelemetry):
        instance = cls.empty()
        instance.pus_tm = tm
        Service20FsfwTm.__common_checks(instance.pus_tm)
        return instance

    def pack(self) -> bytes:
        return self.pus_tm.pack()

    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        return self.pus_tm.time_provider

    @property
    def object_id(self) -> bytes:
        return bytes(self.source_data[0:4])

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    @classmethod
    def empty(cls) -> Service20FsfwTm:
        return cls(
            subservice=0,
            time_provider=CdsShortTimestamp.empty(),
            apid=0,
            source_data=bytes([0, 0, 0, 0]),
        )

    def __eq__(self, other: Service20FsfwTm):
        return self.pus_tm == other.pus_tm
