import enum
import struct

from tmtccmd.ecss.tc import PusTelecommand


class Srv3Subservice(enum.IntEnum):
    ENABLE_PERIODIC_HK_GEN = 5,
    DISABLE_PERIODIC_HK_GEN = 6,
    ENABLE_PERIODIC_DIAGNOSTICS_GEN = 7,
    DISABLE_PERIODIC_DIAGNOSTICS_GEN = 8,

    REPORT_HK_REPORT_STRUCTURES = 9,
    REPORT_DIAG_REPORT_STRUCTURES = 11,

    HK_DEFINITIONS_REPORT = 10,
    DIAG_DEFINITION_REPORT = 12,

    HK_REPORT = 25,
    DIAGNOSTICS_REPORT = 26,

    GENERATE_ONE_PARAMETER_REPORT = 27,
    GENERATE_ONE_DIAGNOSTICS_REPORT = 28,

    MODIFY_PARAMETER_REPORT_COLLECTION_INTERVAL = 31,
    MODIFY_DIAGNOSTICS_REPORT_COLLECTION_INTERVAL = 32,


def make_sid(object_id: bytearray, set_id: int) -> bytearray:
    set_id_bytearray = struct.pack(">I", set_id)
    return object_id + set_id_bytearray


def make_interval(interval_seconds: float) -> bytearray:
    return bytearray(struct.pack("!f", interval_seconds))


def generate_one_hk_command(sid: bytearray, ssc: int):
    return PusTelecommand(service=3, subservice=27, ssc=ssc, app_data=sid)


def generate_one_diag_command(sid: bytearray, ssc: int):
    return PusTelecommand(service=3, subservice=28, ssc=ssc, app_data=sid)
