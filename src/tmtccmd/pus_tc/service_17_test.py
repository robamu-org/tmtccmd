import enum

from tmtccmd.core.definitions import QueueCommands
from tmtccmd.pus_tc.base import PusTelecommand, TcQueueT


class Srv17Subservices(enum.IntEnum):
    PING_CMD = 1,
    GEN_EVENT = 128


def pack_service17_ping_command(ssc: int) -> PusTelecommand:
    return PusTelecommand(service=17, subservice=Srv17Subservices.PING_CMD, ssc=ssc)


def pack_generic_service17_test(init_ssc: int, tc_queue: TcQueueT) -> int:
    new_ssc = init_ssc
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17"))
    # ping test
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Ping Test"))
    tc_queue.appendleft(pack_service17_ping_command(ssc=new_ssc).pack_command_tuple())
    new_ssc += 1
    # enable event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Enable Event"))
    command = PusTelecommand(service=5, subservice=5, ssc=new_ssc)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # test event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Trigger event"))
    command = PusTelecommand(service=17, subservice=Srv17Subservices.GEN_EVENT, ssc=new_ssc)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # invalid subservice
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Invalid subservice"))
    command = PusTelecommand(service=17, subservice=243, ssc=new_ssc)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    return new_ssc
