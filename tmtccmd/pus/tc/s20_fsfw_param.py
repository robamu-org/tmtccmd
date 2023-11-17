"""Contains definitions and functions related to PUS Service 20 Telecommands.
"""
from __future__ import annotations
import struct

from spacepackets.ecss import PusService
from tmtccmd.version import get_version
from deprecation import deprecated
from typing import Optional

from spacepackets.ecss.fields import Ptc, PfcUnsigned, PfcReal
from tmtccmd.pus.s20_fsfw_param_defs import (  # noqa: F401
    CustomSubservice,
    create_scalar_boolean_parameter,
    create_scalar_u8_parameter,
    create_scalar_u16_parameter,
    create_scalar_u32_parameter,
    create_scalar_i8_parameter,
    create_scalar_i16_parameter,
    create_scalar_i32_parameter,
    create_scalar_float_parameter,
    create_scalar_double_parameter,
    create_vector_double_parameter,
    create_vector_float_parameter,
    create_matrix_float_parameter,
    create_matrix_double_parameter,
    Parameter,
    FsfwParamId,
)
from spacepackets.ecss.tc import PusTelecommand


def create_load_param_cmd(parameter: Parameter) -> PusTelecommand:
    return PusTelecommand(
        service=PusService.S20_PARAMETER,
        subservice=CustomSubservice.TC_LOAD,
        app_data=parameter.pack(),
    )


def create_dump_param_cmd(param_fsfw_id: FsfwParamId) -> PusTelecommand:
    return PusTelecommand(
        service=PusService.S20_PARAMETER,
        subservice=CustomSubservice.TC_LOAD,
        app_data=param_fsfw_id.pack(),
    )


def create_load_param_cmd_from_raw(parameter_raw: bytes) -> PusTelecommand:
    return PusTelecommand(
        service=PusService.S20_PARAMETER,
        subservice=CustomSubservice.TC_LOAD,
        app_data=parameter_raw,
    )


@deprecated(
    deprecated_in="4.0.0a3",
    current_version=get_version(),
    details="Please use crate_fsfw_load_param_cmd instead",
)
def pack_fsfw_load_param_cmd(app_data: bytes) -> PusTelecommand:
    return create_load_param_cmd(app_data)


@deprecated(
    deprecated_in="3.1.0",
    current_version=get_version(),
    details="Please use create_scalar_boolean_parameter instead",
)
def pack_boolean_parameter_app_data(
    object_id: bytes, domain_id: int, unique_id: int, parameter: bool
) -> Optional[bytearray]:
    return pack_scalar_boolean_parameter_app_data(
        object_id, domain_id, unique_id, parameter
    )


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use create_scalar_boolean_parameter instead",
)
def pack_scalar_boolean_parameter_app_data(
    object_id: bytes, domain_id: int, unique_id: int, parameter: bool
) -> Optional[bytearray]:
    """Tailored towards FSFW applications.

    :param object_id:
    :param domain_id:
    :param unique_id:
    :param parameter:
    :return: Application data
    """
    return pack_scalar_u8_parameter_app_data(
        object_id, domain_id, unique_id, int(parameter)
    )


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use create_scalar_u8_parameter instead",
)
def pack_scalar_u8_parameter_app_data(
    object_id: bytes, domain_id: int, unique_id: int, parameter: int
) -> Optional[bytearray]:
    """Tailored towards FSFW applications.

    :param object_id:
    :param domain_id:
    :param unique_id:
    :param parameter:
    :return: Application data
    """
    data_to_pack = prepare_param_packet_header(
        object_id=object_id,
        domain_id=domain_id,
        unique_id=unique_id,
        ptc=Ptc.UNSIGNED,
        pfc=PfcUnsigned.ONE_BYTE,
        rows=1,
        columns=1,
    )
    if data_to_pack is not None:
        data_to_pack.append(parameter)
    return data_to_pack


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use create_scalar_double_parameter instead",
)
def pack_scalar_double_param_app_data(
    object_id: bytes, domain_id: int, unique_id: int, parameter: float
) -> Optional[bytearray]:
    data_to_pack = prepare_param_packet_header(
        object_id=object_id,
        domain_id=domain_id,
        unique_id=unique_id,
        ptc=Ptc.REAL,
        pfc=PfcReal.DOUBLE_PRECISION_IEEE,
        rows=1,
        columns=1,
    )
    if data_to_pack is not None:
        data_to_pack.extend(struct.pack("!d", parameter))
    return data_to_pack


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use create_scalar_float_parameter instead",
)
def pack_scalar_float_param_app_data(
    object_id: bytes, domain_id: int, unique_id: int, parameter: float
) -> Optional[bytearray]:
    data_to_pack = prepare_param_packet_header(
        object_id=object_id,
        domain_id=domain_id,
        unique_id=unique_id,
        ptc=Ptc.REAL,
        pfc=PfcReal.FLOAT_SIMPLE_PRECISION_IEEE,
        rows=1,
        columns=1,
    )
    if data_to_pack is not None:
        data_to_pack.extend(struct.pack("!f", parameter))
    return data_to_pack


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use ParamWrapper helper class with pack() instead",
)
def prepare_param_packet_header(
    object_id: bytes,
    domain_id: int,
    unique_id: int,
    ptc: Ptc,
    pfc: int,
    rows: int,
    columns: int,
    start_at_idx: int = 0,
) -> Optional[bytearray]:
    parameter_id = bytearray(4)
    parameter_id[0] = domain_id
    if unique_id > 255:
        raise ValueError("Invalid unique ID, should be smaller than 255!")
    parameter_id[1] = unique_id
    parameter_id[2] = (start_at_idx >> 8) & 0xFF
    parameter_id[3] = start_at_idx & 0xFF
    data_to_pack = bytearray(object_id)
    data_to_pack.extend(parameter_id)
    data_to_pack.extend(
        pack_type_and_matrix_data(ptc=ptc, pfc=pfc, rows=rows, columns=columns)
    )
    return data_to_pack


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use ParamWrapper helper class with pack() instead",
)
def pack_type_and_matrix_data(ptc: int, pfc: int, rows: int, columns: int) -> bytearray:
    data = bytearray(4)
    data[0] = ptc
    data[1] = pfc
    data[2] = rows
    data[3] = columns
    return data


@deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="Please use ParameterId helper class with pack() instead",
)
def pack_parameter_id(domain_id: int, unique_id: int, linear_index: int) -> bytearray:
    """Packs the Parameter ID (bytearray with 4 bytes) which is part of the service 20 packets.
    The first byte of the parameter ID is the domain ID, the second byte is a unique ID and the
    last two bytes are a linear index if a parameter is not loaded from index 0.
    :param domain_id:       One byte domain ID
    :param unique_id:       One byte unique ID
    :param linear_index:    Two byte linear index.
    """
    parameter_id = bytearray(4)
    parameter_id[0] = domain_id
    parameter_id[1] = unique_id
    parameter_id[2] = linear_index >> 8 & 0xFF
    parameter_id[3] = linear_index & 0xFF
    return parameter_id
