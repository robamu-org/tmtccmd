# -*- coding: utf-8 -*-
from typing import Deque, List, Tuple, Optional
from tmtccmd.ccsds.handler import CcsdsHandler
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus_tm.service_5_event import Service5TM
from tmtccmd.pus_tm.service_1_verification import Service1TM
from tmtccmd.pus_tm.service_17_test import Service17TM
from tmtccmd.utility.logger import get_logger

LOGGER = get_logger()
PusTmTupleT = Tuple[bytearray, PusTelemetry]

TelemetryListT = List[bytearray]
TelemetryQueueT = Deque[TelemetryListT]

PusTmListT = List[PusTelemetry]
PusTmQueueT = Deque[PusTmListT]

PusTmListT = List[PusTelemetry]
PusTmObjQeue = Deque[PusTelemetry]
PusTmTupleQueueT = Deque[PusTmTupleT]


class PusTmHandler(CcsdsHandler):
    """Deserialize TM bytearrays into PUS TM Classes"""
    def __init__(self, apid: int):
        super().__init__(apid=apid)

    @abstractmethod
    def handle_ccsds_packet(self, packet: bytearray):
        return default_factory_hook(raw_tm_packet=packet)


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
