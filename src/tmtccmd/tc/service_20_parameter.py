from typing import Union

from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.pus.service_20_parameter import EcssPtc, EcssPfcUnsigned
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.config.globals import get_global_apid

logger = get_console_logger()


def pack_boolean_parameter_command(
        object_id: bytearray, domain_id: int, unique_id: int, parameter: bool, ssc: int,
        apid: int = -1
) -> Union[PusTelecommand, None]:
    """
    Generic function to pack a telecommand to tweak a boolean parameter
    :param object_id:
    :param domain_id:
    :param unique_id:
    :param parameter:
    :param ssc:
    :param apid:
    @return:
    """
    if apid == -1:
        apid = get_global_apid()

    parameter_id = bytearray(4)
    parameter_id[0] = domain_id
    if unique_id > 255:
        logger.warning("Invalid unique ID, should be smaller than 255!")
        return None
    parameter_id[1] = unique_id
    parameter_id[2] = 0
    parameter_id[3] = 0
    data_to_pack = bytearray(object_id)
    data_to_pack.extend(parameter_id)
    # PTC and PFC for uint8_t according to CCSDS
    ptc = EcssPtc.UNSIGNED
    pfc = EcssPfcUnsigned.ONE_BYTE
    rows = 1
    columns = 1
    data_to_pack.append(ptc)
    data_to_pack.append(pfc)
    data_to_pack.append(rows)
    data_to_pack.append(columns)
    data_to_pack.append(parameter)
    return PusTelecommand(service=20, subservice=128, ssc=ssc, app_data=data_to_pack, apid=apid)


def pack_float_vector_parameter_command(
        object_id: bytearray, domain_id: int, unique_id: int, parameter: bytearray, ssc: int,
        apid: int = -1
):
    pass


def pack_type_and_matrix_data(ptc: int, pfc: int, rows: int, columns: int) -> bytearray:
    # noinspection PyPep8
    """Packs the parameter information field, which contains the ECSS PTC and PFC numbers and the number of columns
    and rows in the parameter.
    See https://ecss.nl/standard/ecss-e-st-70-41c-space-engineering-telemetry-and-telecommand-packet-utilization-15-april-2016/
    p.428 for more information.
    :param ptc:     ECSS PTC number
    :param pfc:     ECSS PFC number
    :param rows:     Number of rows in parameter (for matrix entries, 1 for vector entries, 1 for scalar entries)
    :param columns:  Number of columns in parameter (for matrix or vector entries, 1 for scalar entries)
    :return: Parameter information field as 4 byte bytearray
    """
    data = bytearray(4)
    data[0] = ptc
    data[1] = pfc
    data[2] = rows
    data[3] = columns
    return data


def pack_parameter_id(domain_id: int, unique_id: int, linear_index: int) -> bytearray:
    """Packs the Parameter ID (bytearray with 4 bytes) which is part of the service 20 packets.
    The first byte of the parameter ID is the domain ID, the second byte is a unique ID and the last two bytes are a
    linear index if a parameter is not loaded from index 0.
    :param domain_id:       One byte domain ID
    :param unique_id:       One byte unique ID
    :param linear_index:    Two byte linear index.
    """
    parameter_id = bytearray(4)
    parameter_id[0] = domain_id
    parameter_id[1] = unique_id
    parameter_id[2] = linear_index >> 8 & 0xff
    parameter_id[3] = linear_index & 0xff
    return parameter_id
