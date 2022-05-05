from spacepackets.ecss import PusTelemetry
from tmtccmd.tm.pus_17_test import Service17TMExtended
from tmtccmd.tm import Service5Tm
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()
FSFW_PRINTER = FsfwTmTcPrinter(None)


def default_ccsds_packet_handler(_apid: int, raw_tm_packet: bytes, _user_args: any):
    """Default implementation only prints the packet"""
    default_factory_hook(raw_tm_packet=raw_tm_packet)


def default_factory_hook(raw_tm_packet: bytes):
    printer = FsfwTmTcPrinter(None)
    service_type = raw_tm_packet[7]
    tm_packet = None
    if service_type == 1:
        tm_packet = Service17TMExtended.unpack(raw_telemetry=raw_tm_packet)
    if service_type == 5:
        tm_packet = Service5Tm.unpack(raw_telemetry=raw_tm_packet)
    if service_type == 17:
        tm_packet = Service17TMExtended.unpack(raw_telemetry=raw_tm_packet)
    if tm_packet is None:
        LOGGER.info(
            f"The service {service_type} is not implemented in Telemetry Factory"
        )
        tm_packet = PusTelemetry.unpack(raw_telemetry=raw_tm_packet)
    printer.handle_long_tm_print(packet_if=tm_packet, info_if=tm_packet)
