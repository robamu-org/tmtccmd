from __future__ import annotations

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl
from spacepackets.ecss import (
    Ptc,
    PusTelemetry,
)
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import AbstractPusTm

from tmtccmd.pus.s20_fsfw_param import (
    CustomSubservice,
)
from tmtccmd.pus.s20_fsfw_param_defs import ParameterId, Parameter, FsfwParamId


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
            fsfw_param_id=FsfwParamId(
                object_id=self.param_tm.source_data[0:4],
                param_id=param_id,
                ptc=Ptc(ptc),
                pfc=pfc,
                rows=rows,
                columns=columns,
            ),
            param_raw=param_data,
        )


class Service20FsfwTm(AbstractPusTm):
    def __init__(
        self,
        subservice: int,
        source_data: bytes,
        timestamp: bytes,
        apid: int = 0,
    ):
        self.pus_tm = PusTelemetry(
            service=PusService.S20_PARAMETER,
            subservice=subservice,
            source_data=source_data,
            timestamp=timestamp,
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
    def unpack(cls, raw_telemetry: bytes, timestamp_len: int) -> Service20FsfwTm:
        instance = cls.empty()
        instance.pus_tm = PusTelemetry.unpack(
            data=raw_telemetry, timestamp_len=timestamp_len
        )
        Service20FsfwTm.__common_checks(instance.pus_tm)
        return instance

    @classmethod
    def from_tm(cls, tm: PusTelemetry):
        instance = cls.empty()
        instance.pus_tm = tm
        Service20FsfwTm.__common_checks(instance.pus_tm)
        return instance

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @property
    def timestamp(self) -> bytes:
        return self.pus_tm.timestamp

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
            apid=0,
            source_data=bytes([0, 0, 0, 0]),
            timestamp=bytes(),
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def ccsds_version(self) -> int:
        return self.pus_tm.ccsds_version

    @property
    def packet_id(self) -> PacketId:
        return self.pus_tm.packet_id

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.pus_tm.packet_seq_control

    def __eq__(self, other: object):
        if not isinstance(other, Service20FsfwTm):
            return False
        return self.pus_tm == other.pus_tm
