from abc import abstractmethod

from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.config.globals import get_global, CoreGlobalIds
from tmtccmd.pus_tm.service_5_event import Service5TM
from tmtccmd.pus_tm.service_1_verification import Service1TM
from tmtccmd.pus_tm.service_17_test import Service17TM
from tmtccmd.utility.logger import get_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter

LOGGER = get_logger()


def default_ccsds_packet_handler(self, apid: int, packet: bytearray):
    """Default implementation only prints the packet"""
    telemetry_packet = default_factory_hook(raw_tm_packet=packet)
    tmtc_printer = get_global(CoreGlobalIds.TMTC_PRINTER_HANDLE)
    tmtc_printer.print_telemetry(packet=telemetry_packet)


def default_factory_hook(raw_tm_packet: bytearray) -> PusTelemetry:
    service_type = raw_tm_packet[7]
    if service_type == 1:
        return Service1TM(raw_tm_packet)
    if service_type == 5:
        return Service5TM(raw_tm_packet)
    if service_type == 17:
        return Service17TM(raw_tm_packet)
    LOGGER.info("The service " + str(service_type) + " is not implemented in the default TM Factory function")
    return PusTelemetry(raw_tm_packet)
