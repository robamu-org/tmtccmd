from tmtccmd.ccsds.handler import CcsdsTmHandler
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus_tm.service_5_event import Service5TM
from tmtccmd.pus_tm.service_1_verification import Service1TM
from tmtccmd.pus_tm.service_17_test import Service17TM
from tmtccmd.utility.logger import get_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter

LOGGER = get_logger()


class PusTmHandler(CcsdsTmHandler):
    """Deserialize TM bytearrays into PUS TM Classes"""
    def __init__(self, apid: int, tmtc_printer: TmTcPrinter):
        super().__init__(apid=apid)
        self.tmtc_printer = tmtc_printer

    def handle_ccsds_packet(self, packet: bytearray):
        """Default implementation only prints the packet"""
        telemetry_packet = default_factory_hook(raw_tm_packet=packet)
        self.tmtc_printer.print_telemetry(packet=telemetry_packet)


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
