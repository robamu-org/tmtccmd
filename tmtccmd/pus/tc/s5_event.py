"""Contains definitions and functions related to PUS Service 5 Telecommands.
"""

from deprecated.sphinx import deprecated
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_5_event import Subservice


@deprecated(
    version="v4.0.0a0",
    reason="use create... API instead",
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


@deprecated(
    version="v4.0.0a0",
    reason="use create... API instead",
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
