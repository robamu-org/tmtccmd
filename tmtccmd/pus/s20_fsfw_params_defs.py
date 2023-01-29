from __future__ import annotations
import dataclasses
import enum
import struct
from typing import Optional, Union

from spacepackets.ecss import Ptc, PfcUnsigned, PfcSigned, PfcReal


class CustomSubservice(enum.IntEnum):
    TC_LOAD = 128
    TC_DUMP = 129
    TM_DUMP_REPLY = 130


@dataclasses.dataclass
class ParameterId:
    domain_id: int
    unique_id: int
    linear_index: int

    @classmethod
    def empty(cls) -> ParameterId:
        return cls(0, 0, 0)

    def as_u32(self) -> int:
        return (self.domain_id << 24) | (self.unique_id << 16) | self.linear_index

    def pack(self) -> bytes:
        raw = bytearray([self.domain_id, self.unique_id])
        raw.extend(struct.pack("!H", self.linear_index))
        return raw

    @classmethod
    def unpack(cls, data: bytes) -> ParameterId:
        if len(data) < 4:
            raise ValueError("raw parameter ID must be at least 4 bytes wide")
        domain_id = data[0]
        unique_id = data[1]
        linear_index = struct.unpack("!H", data[2:4])[0]
        return cls(domain_id, unique_id, linear_index)


@dataclasses.dataclass
class Parameter:
    """Wrapper for the whole FSFW specific parameter data.
     It contains the ECSS PTC and PFC numbers and the number of columns and rows in the parameter.
    See https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/
    p.428 for more information.

    :param ptc:     ECSS PTC number
    :param pfc:     ECSS PFC number
    :param rows:     Number of rows in parameter (for matrix entries, 1 for vector entries,
        1 for scalar entries)
    :param columns:  Number of columns in parameter (for matrix or vector entries,
        1 for scalar entries)
    :return: Parameter information field as 4 byte bytearray
    """  # noqa: E501

    object_id: bytes
    param_id: ParameterId
    ptc: Optional[Ptc]
    pfc: int
    rows: int
    columns: int
    param_raw: bytes

    @classmethod
    def empty(cls):
        return cls(
            object_id=bytes([0, 0, 0, 0]),
            param_id=ParameterId.empty(),
            ptc=None,
            pfc=0,
            rows=0,
            columns=0,
            param_raw=bytes(),
        )

    def pack(self) -> bytes:
        """Convert the wrapper to the raw byte format expected for PUS TC or PUS TM creation."""
        raw = bytearray(self.object_id)
        raw.extend(self.param_id.pack())
        raw.append(self.ptc)
        raw.append(self.pfc)
        raw.append(self.rows)
        raw.append(self.columns)
        raw.extend(self.param_raw)
        return raw

    @classmethod
    def unpack(cls, data: bytes) -> Parameter:
        if len(data) < 12:
            raise ValueError("passed raw parameter data size smaller than 12 bytes")
        try:
            ptc = Ptc(data[8])
        except TypeError:
            raise ValueError(f"ptc with unknown raw value {data[8]}")
        return cls(
            object_id=data[0:4],
            param_id=ParameterId.unpack(data[4:8]),
            ptc=ptc,
            pfc=data[9],
            rows=data[10],
            columns=data[11],
            param_raw=data[12:],
        )

    def parse_scalar_param(self) -> Union[int, float]:
        return parse_scalar_param(self)


def parse_scalar_param(wrapper: Parameter) -> Union[int, float]:
    return deserialize_scalar_entry(wrapper.ptc, wrapper.pfc, wrapper.param_raw)


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


def create_scalar_boolean_parameter(
    object_id: bytes, domain_id: int, unique_id: int, parameter: bool
) -> Parameter:
    return create_scalar_u8_parameter(object_id, domain_id, unique_id, int(parameter))


def create_scalar_u8_parameter(
    object_id: bytes, domain_id: int, unique_id: int, parameter: int
) -> Parameter:
    if parameter < 0 or parameter > pow(2, 8) - 1:
        raise ValueError(f"parameter {parameter} is not a valid u8")
    return Parameter(
        object_id=object_id,
        param_id=ParameterId(domain_id, unique_id, 0),
        ptc=Ptc.UNSIGNED,
        pfc=PfcUnsigned.ONE_BYTE,
        rows=1,
        columns=1,
        param_raw=bytes([parameter]),
    )


def create_scalar_double_parameter(
    object_id: bytes, domain_id: int, unique_id: int, parameter: float
) -> Parameter:
    return Parameter(
        object_id=object_id,
        param_id=ParameterId(domain_id, unique_id, 0),
        ptc=Ptc.REAL,
        pfc=PfcReal.DOUBLE_PRECISION_IEEE,
        rows=1,
        columns=1,
        param_raw=struct.pack("!d", parameter),
    )


def create_scalar_float_parameter(
    object_id: bytes, domain_id: int, unique_id: int, parameter: float
) -> Parameter:
    return Parameter(
        object_id=object_id,
        param_id=ParameterId(domain_id, unique_id, 0),
        ptc=Ptc.REAL,
        pfc=PfcReal.FLOAT_SIMPLE_PRECISION_IEEE,
        rows=1,
        columns=1,
        param_raw=struct.pack("!f", parameter),
    )
