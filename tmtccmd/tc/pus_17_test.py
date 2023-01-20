import deprecation

from tmtccmd import __version__
from spacepackets.ecss import PusTelecommand, PusService
from spacepackets.ecss.pus_17_test import Subservice


@deprecation.deprecated(
    deprecated_in="v4.0.0a2",
    current_version=__version__,
    details="use create... API instead",
)
def pack_service_17_ping_command(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return create_service_17_ping_command(apid, seq_count)


def create_service_17_ping_command(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    return PusTelecommand(
        service=PusService.S17_TEST,
        subservice=Subservice.TC_PING,
        apid=apid,
        seq_count=seq_count,
    )
