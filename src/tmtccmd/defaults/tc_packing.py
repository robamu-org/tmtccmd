import os
from collections import deque

from tmtccmd.pus_tc.definitions import TcQueueT
from tmtccmd.core.definitions import CoreServiceList
from tmtccmd.pus_tc.service_17_test import pack_service17_ping_command
from tmtccmd.pus_tc.service_5_event import pack_generic_service5_test_into
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


def default_service_queue_preparation(service: int, op_code: str, service_queue: TcQueueT):
    from tmtccmd.pus_tc.service_5_event import pack_generic_service5_test_into
    from tmtccmd.pus_tc.service_17_test import pack_service17_ping_command

    if service == CoreServiceList.SERVICE_5:
        return pack_generic_service5_test_into(service_queue)
    if service == CoreServiceList.SERVICE_17:
        return service_queue.appendleft(pack_service17_ping_command(ssc=1700).pack_command_tuple())
    LOGGER.warning("Invalid Service !")


def default_total_queue_preparation() -> TcQueueT:
    if not os.path.exists("log"):
        os.mkdir("log")
    tc_queue = deque()
    pack_generic_service5_test_into(tc_queue)
    tc_queue.appendleft(pack_service17_ping_command(ssc=1700).pack_command_tuple())
    return tc_queue
