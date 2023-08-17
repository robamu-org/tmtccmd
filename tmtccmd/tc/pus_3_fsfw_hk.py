"""Contains definitions and functions related to PUS Service 3 Telecommands.
"""
import struct
import deprecation
from typing import Tuple

from tmtccmd.version import get_version
from spacepackets.ecss.tc import PusTelecommand
from spacepackets.ecss.pus_3_hk import Subservice


def make_sid(object_id: bytes, set_id: int) -> bytearray:
    sid_raw = bytearray()
    sid_raw += object_id + struct.pack(">I", set_id)
    return sid_raw


def make_interval(interval_seconds: float) -> bytearray:
    return bytearray(struct.pack("!f", interval_seconds))


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def enable_periodic_hk_command(diag: bool, sid: bytes) -> PusTelecommand:
    return create_enable_periodic_hk_command_with_diag(diag, sid)


def create_enable_periodic_hk_command(sid: bytes) -> PusTelecommand:
    return __generate_periodic_hk_command(enable=True, sid=sid)


@deprecation.deprecated(
    deprecated_in="v6.0.0rc0",
    current_version=get_version(),
    details="use diagnostic agnostic API if possible",
)
def create_enable_periodic_hk_command_with_diag(
    diag: bool, sid: bytes
) -> PusTelecommand:
    return __generate_periodic_hk_command_legacy(diag=diag, enable=True, sid=sid)


@deprecation.deprecated(
    deprecated_in="v6.0.0rc0",
    current_version=get_version(),
    details="use diagnostic agnostic API if possible",
)
def create_enable_periodic_hk_command_with_interval_with_diag(
    diag: bool, sid: bytes, interval_seconds: float
) -> Tuple[PusTelecommand, PusTelecommand]:
    cmd0 = create_modify_collection_interval_cmd_with_diag(diag, sid, interval_seconds)
    cmd1 = __generate_periodic_hk_command_legacy(diag=diag, enable=True, sid=sid)
    return cmd0, cmd1


def create_enable_periodic_hk_command_with_interval(
    sid: bytes, interval_seconds: float
) -> Tuple[PusTelecommand, PusTelecommand]:
    cmd0 = create_modify_collection_interval_cmd(sid, interval_seconds)
    cmd1 = __generate_periodic_hk_command(enable=True, sid=sid)
    return cmd0, cmd1


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def enable_periodic_hk_command_with_interval(
    diag: bool, sid: bytes, interval_seconds: float
) -> Tuple[PusTelecommand, PusTelecommand]:
    return create_enable_periodic_hk_command_with_interval_with_diag(
        diag, sid, interval_seconds
    )


def create_disable_periodic_hk_command(sid: bytes) -> PusTelecommand:
    return __generate_periodic_hk_command(enable=False, sid=sid)


@deprecation.deprecated(
    deprecated_in="v6.0.0rc0",
    current_version=get_version(),
    details="use diagnostic agnostic API if possible",
)
def create_disable_periodic_hk_command_with_diag(
    diag: bool, sid: bytes
) -> PusTelecommand:
    return __generate_periodic_hk_command_legacy(diag=diag, enable=False, sid=sid)


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def disable_periodic_hk_command(diag: bool, sid: bytes) -> PusTelecommand:
    return create_disable_periodic_hk_command_with_diag(diag, sid)


def __generate_periodic_hk_command(enable: bool, sid: bytes) -> PusTelecommand:
    app_data = bytearray(sid)
    if enable:
        subservice = Subservice.TC_ENABLE_PERIODIC_HK_GEN
    else:
        subservice = Subservice.TC_DISABLE_PERIODIC_HK_GEN
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


def __generate_periodic_hk_command_legacy(
    diag: bool, enable: bool, sid: bytes
) -> PusTelecommand:
    app_data = bytearray(sid)
    if enable:
        if diag:
            subservice = Subservice.TC_ENABLE_PERIODIC_DIAGNOSTICS_GEN
        else:
            subservice = Subservice.TC_ENABLE_PERIODIC_HK_GEN
    else:
        if diag:
            subservice = Subservice.TC_DISABLE_PERIODIC_DIAGNOSTICS_GEN
        else:
            subservice = Subservice.TC_DISABLE_PERIODIC_HK_GEN
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def modify_collection_interval(
    diag: bool, sid: bytes, interval_seconds: float
) -> PusTelecommand:
    return create_modify_collection_interval_cmd_with_diag(diag, sid, interval_seconds)


def create_modify_collection_interval_cmd(
    sid: bytes, interval_seconds: float
) -> PusTelecommand:
    app_data = bytearray(sid)
    app_data += make_interval(interval_seconds)
    subservice = Subservice.TC_MODIFY_PARAMETER_REPORT_COLLECTION_INTERVAL
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


@deprecation.deprecated(
    deprecated_in="v6.0.0rc0",
    current_version=get_version(),
    details="use diagnostic agnostic API if possible",
)
def create_modify_collection_interval_cmd_with_diag(
    diag: bool, sid: bytes, interval_seconds: float
) -> PusTelecommand:
    app_data = bytearray(sid)
    app_data += make_interval(interval_seconds)
    if diag:
        subservice = Subservice.TC_MODIFY_DIAGNOSTICS_REPORT_COLLECTION_INTERVAL
    else:
        subservice = Subservice.TC_MODIFY_PARAMETER_REPORT_COLLECTION_INTERVAL
    return PusTelecommand(service=3, subservice=subservice, app_data=app_data)


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_one_hk_command(sid: bytes) -> PusTelecommand:
    return create_request_one_hk_command(sid)


def create_request_one_hk_command(sid: bytes) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservice.TC_GENERATE_ONE_PARAMETER_REPORT,
        app_data=sid,
    )


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_one_diag_command(sid: bytes) -> PusTelecommand:
    return create_request_one_diag_command(sid)


def create_request_one_diag_command(sid: bytes) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservice.TC_GENERATE_ONE_DIAGNOSTICS_REPORT,
        app_data=sid,
    )
