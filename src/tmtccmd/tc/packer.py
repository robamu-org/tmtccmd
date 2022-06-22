# -*- coding: utf-8 -*-
"""
:file:      obsw_tc_packer.py
:author:    R. Mueller
:date:      10.05.2021
"""
import sys
from typing import Union

from tmtccmd.tc.definitions import QueueHelper
from spacepackets.ecss.tc import PusTelecommand
from tmtccmd.logging import get_console_logger
from tmtccmd.pus.pus_17_test import pack_service_17_ping_command
from tmtccmd.tc.pus_5_event import pack_generic_service5_test_into

LOGGER = get_console_logger()


"""
class ServiceQueuePacker:
    def __init__(self):
        pass

    @staticmethod
    def pack_service_queue_core(service: int, op_code: str, service_queue: TcQueueT):
        try:
            from tmtccmd.config.hook import get_global_hook_obj

            hook_obj = get_global_hook_obj()
            hook_obj.pack_service_queue(
                service=service, op_code=op_code, tc_queue=service_queue
            )
        except ImportError:
            LOGGER.exception(
                "Could not import custom telecommand hook! Make sure to implement it."
            )
            sys.exit(1)
"""


def ping_queue(service_queue: QueueHelper):
    from tmtccmd.config.definitions import CoreServiceList, QueueCommands

    service_queue.appendleft((QueueCommands.PRINT, "Sending ping command PUS TC[17,1]"))
    service_queue.appendleft(
        pack_service_17_ping_command(ssc=1700).pack_command_tuple()
    )
