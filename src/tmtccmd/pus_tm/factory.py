# -*- coding: utf-8 -*-
from typing import Deque, List, Tuple, Union
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus_tm.service_5_event import Service5TM
from tmtccmd.pus_tm.service_1_verification import Service1TM
from tmtccmd.pus_tm.service_17_test import Service17TM
from tmtccmd.utility.logger import get_logger

LOGGER = get_logger()
PusRawTmList = List[bytearray]
PusRawTmQueue = Deque[bytearray]
PusTmTupleT = Tuple[bytearray, PusTelemetry]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]

PusTmObjQeue = Deque[PusTelemetry]
PusTmTupleQueueT = Deque[PusTmTupleT]


class PusTelemetryFactory(object):
    """
    Deserialize TM bytearrays into PUS TM Classes
    """
    @staticmethod
    def create(raw_tm_packet: bytearray) -> Union[PusTelemetry, None]:
        try:
            from tmtccmd.config.hook import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            return hook_obj.tm_user_factory_hook(raw_tm_packet=raw_tm_packet)
        except ValueError:
            LOGGER.error("PusTelemetryFactory:create: Invalid packet format")
            return None


def default_factory_hook(raw_tm_packet: bytearray) -> PusTelemetry:
    service_type = raw_tm_packet[7]
    if service_type == 1:
        return Service1TM(raw_tm_packet)
    if service_type == 5:
        return Service5TM(raw_tm_packet)
    if service_type == 17:
        return Service17TM(raw_tm_packet)
    LOGGER.info("The service " + str(service_type) + " is not implemented in Telemetry Factory")
    return PusTelemetry(raw_tm_packet)
