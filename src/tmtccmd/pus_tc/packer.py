# -*- coding: utf-8 -*-
"""
@file   obsw_tc_packer.py
@details
This file transfers TC packing to the user application.
@author R. Mueller
@date   01.11.2019
"""
import sys

from tmtccmd.pus_tc.definitions import TcQueueT
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class ServiceQueuePacker:
    def __init__(self):
        pass

    @staticmethod
    def pack_service_queue_core(service: int, op_code: str, service_queue: TcQueueT):
        """
        Use hook object supplied by user
        """
        try:
            from tmtccmd.config.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            hook_obj.pack_service_queue(
                service=service, op_code=op_code, service_queue=service_queue
            )
        except ImportError:
            LOGGER.exception(
                "Could not import custom telecommand hook! Make sure to implement it."
            )
            sys.exit(1)


