from __future__ import annotations
import enum

from spacepackets.ecss import PusTelecommand, PusServices
from spacepackets.ecss.pus_17_test import Subservices
from tmtccmd.tc.queue import QueueHelperBase


class CustomSubservices(enum.IntEnum):
    TC_GEN_EVENT = 128


def pack_service_17_ping_command() -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    return PusTelecommand(
        service=PusServices.S17_TEST, subservice=Subservices.TC_PING.value
    )


def pack_generic_service17_test(q: QueueHelperBase):
    q.add_log_cmd("Testing Service 17")
    # ping test
    q.add_log_cmd("Testing Service 17: Ping Test")
    q.add_pus_tc(pack_service_17_ping_command())
    # enable event
    q.add_log_cmd("Testing Service 17: Enable Event")
    q.add_pus_tc(PusTelecommand(service=5, subservice=5))
    # test event
    q.add_log_cmd("Testing Service 17: Trigger event")
    q.add_pus_tc(
        PusTelecommand(
            service=17,
            subservice=CustomSubservices.TC_GEN_EVENT,
        )
    )
    # invalid subservice
    q.add_log_cmd("Testing Service 17: Invalid subservice")
    q.add_pus_tc(PusTelecommand(service=17, subservice=243))
