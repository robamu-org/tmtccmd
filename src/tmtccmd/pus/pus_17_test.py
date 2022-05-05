from __future__ import annotations
import enum

from spacepackets.ecss.conf import get_default_tc_apid
from spacepackets.ecss.pus_17_test import Subservices
from tmtccmd.config.definitions import QueueCommands
from tmtccmd.tc.definitions import PusTelecommand, TcQueueT


class CustomSubservices(enum.IntEnum):
    TC_GEN_EVENT = 128


def pack_service_17_ping_command(ssc: int, apid: int = -1) -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    if apid == -1:
        apid = get_default_tc_apid()
    return PusTelecommand(
        service=17, subservice=Subservices.TC_PING.value, ssc=ssc, apid=apid
    )


def pack_generic_service17_test(
    init_ssc: int, tc_queue: TcQueueT, apid: int = -1
) -> int:
    if apid == -1:
        apid = get_default_tc_apid()
    new_ssc = init_ssc
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17"))
    # ping test
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Ping Test"))
    tc_queue.appendleft(pack_service_17_ping_command(ssc=new_ssc).pack_command_tuple())
    new_ssc += 1
    # enable event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Enable Event"))
    command = PusTelecommand(service=5, subservice=5, ssc=new_ssc, apid=apid)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # test event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Trigger event"))
    command = PusTelecommand(
        service=17, subservice=CustomSubservices.TC_GEN_EVENT, ssc=new_ssc, apid=apid
    )
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # invalid subservice
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Invalid subservice"))
    command = PusTelecommand(service=17, subservice=243, ssc=new_ssc, apid=apid)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    return new_ssc
