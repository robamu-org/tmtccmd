from __future__ import annotations
import enum

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.conf import get_default_tc_apid
from spacepackets.ecss.pus_17_test import Subservices
from tmtccmd.tc.queue import QueueHelper


class CustomSubservices(enum.IntEnum):
    TC_GEN_EVENT = 128


def pack_service_17_ping_command(ssc: int, apid: int = -1) -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    if apid == -1:
        apid = get_default_tc_apid()
    return PusTelecommand(
        service=17, subservice=Subservices.TC_PING.value, seq_count=ssc, apid=apid
    )


def pack_generic_service17_test(init_ssc: int, q: QueueHelper, apid: int = -1) -> int:
    if apid == -1:
        apid = get_default_tc_apid()
    new_ssc = init_ssc
    q.add_log_cmd("Testing Service 17")
    # ping test
    q.add_log_cmd("Testing Service 17: Ping Test")
    q.add_pus_tc(pack_service_17_ping_command(ssc=new_ssc))
    new_ssc += 1
    # enable event
    q.add_log_cmd("Testing Service 17: Enable Event")
    q.add_pus_tc(PusTelecommand(service=5, subservice=5, seq_count=new_ssc, apid=apid))
    new_ssc += 1
    # test event
    q.add_log_cmd("Testing Service 17: Trigger event")
    q.add_pus_tc(
        PusTelecommand(
            service=17,
            subservice=CustomSubservices.TC_GEN_EVENT,
            seq_count=new_ssc,
            apid=apid,
        )
    )
    new_ssc += 1
    # invalid subservice
    q.add_log_cmd("Testing Service 17: Invalid subservice")
    q.add_pus_tc(
        PusTelecommand(service=17, subservice=243, seq_count=new_ssc, apid=apid)
    )
    new_ssc += 1
    return new_ssc
