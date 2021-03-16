# -*- coding: utf-8 -*-
from typing import Deque, List, Tuple, Union
from tmtccmd.pus_tm.base import PusTelemetry, PusTmInfoT
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()
PusRawTmList = List[bytearray]
PusRawTmQueue = Deque[bytearray]
PusTmTupleT = Tuple[PusTmInfoT, PusTelemetry]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]

PusTmInfoQueueT = Deque[PusTmInfoT]
PusTmTupleQueueT = Deque[PusTmTupleT]


class PusTelemetryFactory(object):
    """
    Deserialize TM bytearrays into PUS TM Classes
    """
    @staticmethod
    def create(raw_tm_packet: bytearray) -> Union[PusTelemetry, None]:
        try:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            return hook_obj.tm_user_factory_hook(raw_tm_packet=raw_tm_packet)
        except ValueError:
            LOGGER.error("PusTelemetryFactory:create: Invalid packet format")
            return None

