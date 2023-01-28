from __future__ import annotations

import dataclasses
import struct
from typing import Optional, Union

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.time import CdsShortTimestamp, CcsdsTimeProvider
from spacepackets.ecss import (
    Ptc,
    PfcUnsigned,
    PfcSigned,
    PfcReal,
    PusTelemetry,
)
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import AbstractPusTm

from tmtccmd.pus.s20_fsfw_params import (
    CustomSubservice,
)
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


@dataclasses.dataclass
class ParamId:
    domain_id: int
    unique_id: int
    linear_index: int

    @classmethod
    def empty(cls) -> ParamId:
        return cls(0, 0, 0)

    def raw(self) -> int:
        return (self.domain_id << 24) | (self.unique_id << 16) | self.linear_index

    @classmethod
    def from_bytes(cls, data: bytes) -> ParamId:
        if len(data) < 4:
            raise ValueError("raw parameter ID must be at least 4 bytes wide")
        domain_id = data[0]
        unique_id = data[1]
        linear_index = struct.unpack("!H", data[2:4])[0]
        return cls(domain_id, unique_id, linear_index)


@dataclasses.dataclass
class ParamStruct:
    param_id: ParamId
    ptc: Optional[Ptc]
    pfc: int
    row: int
    column: int
    param_data: bytes

    @classmethod
    def empty(cls):
        return cls(
            param_id=ParamId.empty(),
            ptc=None,
            pfc=0,
            row=0,
            column=0,
            param_data=bytes(),
        )

    def parse_scalar_param(self) -> Union[int, float]:
        return deserialize_scalar_entry(self.ptc, self.pfc, self.param_data)


class Service20ParamDumpWrapper:
    def __init__(self, param_tm: Service20FsfwTm):
        self.param_tm = param_tm
        if self.param_tm.subservice != CustomSubservice.TM_DUMP_REPLY:
            raise ValueError(f"subservice is not {CustomSubservice.TM_DUMP_REPLY}")

    @property
    def base_tm(self) -> PusTelemetry:
        return self.param_tm.pus_tm

    def get_param(self) -> ParamStruct:
        """Tries to build a :py:class`ParamStruct` from the own raw telemetry data.

        :raises ValueError: Telemetry source data too short.
        """
        if len(self.param_tm.source_data) < 12:
            raise ValueError("source data too short to hold parameter")
        param_id = ParamId.from_bytes(self.param_tm.source_data[4:8])
        try:
            ptc = Ptc(self.param_tm.source_data[8])
        except TypeError:
            raise ValueError(f"unknown PTC {self.param_tm.source_data[8]}")
        pfc = self.param_tm.source_data[9]
        row = self.param_tm.source_data[10]
        column = self.param_tm.source_data[11]
        param_data = self.param_tm.source_data[12:]
        return ParamStruct(
            param_id=param_id,
            ptc=Ptc(ptc),
            pfc=pfc,
            row=row,
            column=column,
            param_data=param_data,
        )


class Service20FsfwTm(AbstractPusTm):
    def __init__(
        self,
        object_id: bytes,
        subservice: int,
        source_data_after_obj_id: bytes,
        time_provider: Optional[CcsdsTimeProvider],
        apid: int = 0,
    ):
        source_data = bytearray(object_id)
        source_data.extend(source_data_after_obj_id)
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
        cls, raw_telemetry: bytes, time_reader: CcsdsTimeProvider
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

    def get_sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.sp_header

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
            object_id=bytes([0, 0, 0, 0]),
            subservice=0,
            time_provider=CdsShortTimestamp.empty(),
            apid=0,
            source_data_after_obj_id=bytes(),
        )


__BASE_LEN_ERR = "Invalid parameter data size, smaller than "


def __deserialize_unsigned_scalar_entry(
    pfc: int, ptc: int, param_data: bytes, param_len: int
) -> int:
    if pfc == PfcUnsigned.ONE_BYTE:
        if param_len < 1:
            raise ValueError(f"{__BASE_LEN_ERR} 1")
        return param_data[0]
    elif pfc == PfcUnsigned.TWO_BYTES:
        if param_len < 2:
            raise ValueError(f"{__BASE_LEN_ERR} 2")
        return struct.unpack("!H", param_data[0:2])[0]
    if pfc == PfcUnsigned.FOUR_BYTES:
        if param_len < 4:
            raise ValueError(f"{__BASE_LEN_ERR} 4")
        return struct.unpack("!I", param_data[0:4])[0]
    elif pfc == PfcUnsigned.EIGHT_BYTES:
        if param_len < 8:
            raise ValueError(f"{__BASE_LEN_ERR} 8")
        return struct.unpack("!Q", param_data[0:8])[0]
    else:
        raise NotImplementedError(
            f"Parsing of unsigned PTC {ptc} not implemented for PFC {pfc}"
        )


def __deserialize_signed_scalar_entry(
    pfc: int, ptc: int, tm_data: bytes, param_len: int
) -> int:
    if pfc == PfcSigned.ONE_BYTE:
        if param_len < 1:
            raise ValueError(f"{__BASE_LEN_ERR} 1")
        return struct.unpack("!b", tm_data[12:13])[0]
    elif pfc == PfcSigned.TWO_BYTES:
        if param_len < 2:
            raise ValueError(f"{__BASE_LEN_ERR} 2")
        return struct.unpack("!h", tm_data[12:14])[0]
    elif pfc == PfcSigned.FOUR_BYTES:
        if param_len < 4:
            raise ValueError(f"{__BASE_LEN_ERR} 4")
        return struct.unpack("!i", tm_data[12:16])[0]
    elif pfc == PfcSigned.EIGHT_BYTES:
        if param_len < 8:
            raise ValueError(f"{__BASE_LEN_ERR} 8")
        return struct.unpack("!q", tm_data[12:20])[0]
    else:
        raise NotImplementedError(
            f"Parsing of signed PTC {ptc} not implemented for PFC {pfc}"
        )


def deserialize_scalar_entry(
    ptc: int, pfc: int, param_data: bytes
) -> Union[int, float]:
    """Try to deserialize a scalar parameter entry (row = 1 and column = 1).

    :raises ValueError: Passed parameter data length invalid.
    :raises NotImplementedError: Parsing of parameter data not implemented for given PTC and PFC.
    """
    param_len = len(param_data)
    if param_len == 0:
        raise ValueError("passed parameter data is empty")
    if ptc == Ptc.UNSIGNED:
        return __deserialize_unsigned_scalar_entry(pfc, ptc, param_data, param_len)
    elif ptc == Ptc.SIGNED:
        return __deserialize_signed_scalar_entry(pfc, ptc, param_data, param_len)
    if ptc == Ptc.REAL:
        if pfc == PfcReal.FLOAT_SIMPLE_PRECISION_IEEE:
            if param_len < 4:
                raise ValueError(f"{__BASE_LEN_ERR} 4")
            return struct.unpack("!f", param_data[0:4])[0]
        elif pfc == PfcReal.DOUBLE_PRECISION_IEEE:
            if param_len < 8:
                raise ValueError(f"{__BASE_LEN_ERR} 8")
            return struct.unpack("!d", param_data[0:8])[0]
        else:
            raise NotImplementedError(
                f"Parsing of real (floating point) PTC {ptc} not implemented "
                f"for PFC {pfc}"
            )
