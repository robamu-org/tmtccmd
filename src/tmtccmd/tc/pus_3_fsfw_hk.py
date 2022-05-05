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


def generate_one_hk_command(sid: bytes, ssc: int) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservices.TC_GENERATE_ONE_PARAMETER_REPORT,
        ssc=ssc,
        app_data=sid,
    )


def generate_one_diag_command(sid: bytes, ssc: int) -> PusTelecommand:
    return PusTelecommand(
        service=3,
        subservice=Subservices.TC_GENERATE_ONE_DIAGNOSTICS_REPORT,
        ssc=ssc,
        app_data=sid,
    )
