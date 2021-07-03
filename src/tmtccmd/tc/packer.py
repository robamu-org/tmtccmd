# -*- coding: utf-8 -*-
"""
:file:      obsw_tc_packer.py
:author:    R. Mueller
:date:      10.05.2021
"""
import sys
from typing import Union

from tmtccmd.tc.definitions import TcQueueT
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.tc.service_17_test import pack_service17_ping_command
from tmtccmd.tc.service_5_event import pack_generic_service5_test_into

LOGGER = get_console_logger()


class ServiceQueuePacker:
    def __init__(self):
        pass

    @staticmethod
    def pack_service_queue_core(service: int, op_code: str, service_queue: TcQueueT):
        """
        Use hook object supplied by user
        """
        try:
            from tmtccmd.config.hook import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            hook_obj.pack_service_queue(
                service=service, op_code=op_code, service_queue=service_queue
            )
        except ImportError:
            LOGGER.exception(
                "Could not import custom telecommand hook! Make sure to implement it."
            )
            sys.exit(1)


def default_single_packet_preparation() -> PusTelecommand:
    return pack_service17_ping_command(ssc=1700)


def default_service_queue_preparation(service: Union[str, int], op_code: str, service_queue: TcQueueT):
    from tmtccmd.config.definitions import CoreServiceList, QueueCommands
    if service == CoreServiceList.SERVICE_5.value:
        pack_generic_service5_test_into(service_queue)
    if service == CoreServiceList.SERVICE_17.value:
        service_queue.appendleft((QueueCommands.PRINT, "Sending ping command PUS TC[17,1]"))
        service_queue.appendleft(pack_service17_ping_command(ssc=1700).pack_command_tuple())
    else:
        LOGGER.warning("Invalid Service !")
