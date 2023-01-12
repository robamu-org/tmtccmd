"""Contains definitions and functions related to PUS Service 3 Telecommands.
"""
import struct

from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss.pus_3_hk import Subservices


def make_sid(object_id: bytes, set_id: int) -> bytearray:
    sid_raw = bytearray()
    sid_raw += object_id + struct.pack(">I", set_id)
    return sid_raw


def make_interval(interval_seconds: float) -> bytearray:
    return bytearray(struct.pack("!f", interval_seconds))


def enable_periodic_hk_command(diag: bool, sid: bytes) -> PusTelecommand:
    return __generate_periodic_hk_command(diag=diag, enable=True, sid=sid)


def enable_periodic_hk_command_with_interval(
    diag: bool, sid: bytes, interval_seconds: float
) -> (PusTelecommand, PusTelecommand):
    cmd0 = modify_collection_interval(diag, sid, interval_seconds)
    cmd1 = __generate_periodic_hk_command(diag=diag, enable=True, sid=sid)
    return cmd0, cmd1


def disable_periodic_hk_command(diag: bool, sid: bytes) -> PusTelecommand:
    return __generate_periodic_hk_command(diag=diag, enable=False, sid=sid)


def __generate_periodic_hk_command(
    diag: bool, enable: bool, sid: bytes
) -> PusTelecommand:
    app_data = bytearray(sid)
    if enable:
        if diag:
            subservice = Subservices.TC_ENABLE_PERIODIC_DIAGNOSTICS_GEN
        else:
            subservice = Subservices.TC_ENABLE_PERIODIC_HK_GEN
    else:
        if diag:
            subservice = Subservices.TC_DISABLE_PERIODIC_DIAGNOSTICS_GEN
        else:
            subservice = Subservices.TC_DISABLE_PERIODIC_HK_GEN
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


def modify_collection_interval(
    diag: bool, sid: bytes, interval_seconds: float
) -> PusTelecommand:
    app_data = bytearray(sid)
    app_data += make_interval(interval_seconds)
    if diag:
        subservice = Subservices.TC_MODIFY_DIAGNOSTICS_REPORT_COLLECTION_INTERVAL
    else:
        subservice = Subservices.TC_MODIFY_PARAMETER_REPORT_COLLECTION_INTERVAL
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


def generate_one_hk_command(sid: bytes) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservices.TC_GENERATE_ONE_PARAMETER_REPORT,
        app_data=sid,
    )


def generate_one_diag_command(sid: bytes) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservices.TC_GENERATE_ONE_DIAGNOSTICS_REPORT,
        app_data=sid,
    )
