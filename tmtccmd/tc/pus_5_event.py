"""Contains definitions and functions related to PUS Service 5 Telecommands.
"""
from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.conf import get_default_tc_apid
from spacepackets.ecss.pus_5_event import Subservices

from tmtccmd.tc.queue import DefaultPusQueueHelper


def pack_enable_event_reporting_command(ssc: int, apid: int = -1):
    if apid == -1:
        apid = get_default_tc_apid()
    return PusTelecommand(
        service=5,
        subservice=Subservices.TC_ENABLE_EVENT_REPORTING,
        seq_count=ssc,
        apid=apid,
    )


def pack_disable_event_reporting_command(ssc: int, apid: int = -1):
    if apid == -1:
        apid = get_default_tc_apid()
    return PusTelecommand(
        service=5,
        subservice=Subservices.TC_DISABLE_EVENT_REPORTING,
        seq_count=ssc,
        apid=apid,
    )


def pack_generic_service_5_test_into(q: DefaultPusQueueHelper):
    q.add_log_cmd("Testing Service 5")
    # invalid subservice
    q.add_log_cmd("Testing Service 5: Invalid subservice")
    q.add_pus_tc(PusTelecommand(service=5, subservice=1))
    # disable events
    q.add_log_cmd("Testing Service 5: Disable event")
    q.add_pus_tc(pack_disable_event_reporting_command(ssc=501))
    # trigger event
    q.add_log_cmd("Testing Service 5: Trigger event")
    q.add_pus_tc(PusTelecommand(service=17, subservice=128))
    # enable event
    q.add_log_cmd("Testing Service 5: Enable event")
    q.add_pus_tc(pack_enable_event_reporting_command(ssc=520))
    # trigger event
    q.add_log_cmd("Testing Service 5: Trigger another event")
    q.add_pus_tc(PusTelecommand(service=17, subservice=128))
