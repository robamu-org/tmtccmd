"""Contains definitions and functions related to PUS Service 5 Telecommands.
"""
import deprecation

from tmtccmd import __version__
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_5_event import Subservice

from tmtccmd.tc.queue import DefaultPusQueueHelper


@deprecation.deprecated(
    deprecated_in="v4.0.0a0",
    current_version=__version__,
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
    current_version=__version__,
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


def pack_generic_service_5_test_into(q: DefaultPusQueueHelper):
    q.add_log_cmd("Testing Service 5")
    # invalid subservice
    q.add_log_cmd("Testing Service 5: Invalid subservice")
    q.add_pus_tc(PusTelecommand(service=5, subservice=1))
    # disable events
    q.add_log_cmd("Testing Service 5: Disable event")
    q.add_pus_tc(create_disable_event_reporting_command())
    # trigger event
    q.add_log_cmd("Testing Service 5: Trigger event")
    q.add_pus_tc(PusTelecommand(service=17, subservice=128))
    # enable event
    q.add_log_cmd("Testing Service 5: Enable event")
    q.add_pus_tc(create_enable_event_reporting_command())
    # trigger event
    q.add_log_cmd("Testing Service 5: Trigger another event")
    q.add_pus_tc(PusTelecommand(service=17, subservice=128))
