from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.config.globals import get_global, CoreGlobalIds
from tmtccmd.pus_tm.service_5_event import Service5TM
from tmtccmd.pus_tm.service_1_verification import Service1TM
from tmtccmd.pus_tm.service_17_test import Service17TM
from tmtccmd.utility.logger import get_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter

LOGGER = get_logger()


def default_ccsds_packet_handler(apid: int, raw_tm_packet: bytearray, tmtc_printer: TmTcPrinter):
    """Default implementation only prints the packet"""
    default_factory_hook(raw_tm_packet=raw_tm_packet, tmtc_printer=tmtc_printer)


def default_factory_hook(raw_tm_packet: bytearray, tmtc_printer: TmTcPrinter):
    service_type = raw_tm_packet[7]
    tm_packet = None
    if service_type == 1:
        tm_packet = Service1TM(raw_tm_packet)
    if service_type == 5:
        tm_packet = Service5TM(raw_tm_packet)
    if service_type == 17:
        tm_packet = Service17TM(raw_tm_packet)
    if tm_packet is None:
        LOGGER.info(f'The service {service_type} is not implemented in Telemetry Factory')
        tm_packet = PusTelemetry(raw_tm_packet)
    tmtc_printer.print_telemetry(packet=tm_packet)
