"""Contains definitions and functions related to PUS Service 5 Telecommands.
"""
import deprecation

from tmtccmd.version import get_version
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_5_event import Subservice


@deprecation.deprecated(
    deprecated_in="v4.0.0a0",
    current_version=get_version(),
    details="use create... API instead",
)
def pack_enable_event_reporting_command(
    apid: int = 0, seq_count: int = 0
) -> PusTelecommand:
    return create_disable_event_reporting_command(apid, seq_count)


def create_enable_event_reporting_command(
    apid: int = 0, seq_count: int = 0
) -> PusTelecommand:
    return PusTelecommand(
        service=5,
        subservice=Subservice.TC_ENABLE_EVENT_REPORTING,
        seq_count=seq_count,
        apid=apid,
    )


@deprecation.deprecated(
    deprecated_in="v4.0.0a0",
    current_version=get_version(),
    details="use create... API instead",
)
def pack_disable_event_reporting_command(
    apid: int = 0, seq_count: int = 0
) -> PusTelecommand:
    return create_disable_event_reporting_command(apid, seq_count)


def create_disable_event_reporting_command(
    apid: int = 0, seq_count: int = 0
) -> PusTelecommand:
    return PusTelecommand(
        service=5,
        subservice=Subservice.TC_DISABLE_EVENT_REPORTING,
        seq_count=seq_count,
        apid=apid,
    )
