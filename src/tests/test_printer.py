from unittest import TestCase

from tmtccmd.pus_tm.service_1_verification import Service1TmPacked, Service1TM
from tmtccmd.utility.tmtc_printer import TmTcPrinter, DisplayMode
from tmtccmd.utility.tmtcc_logger import get_logger, set_tmtc_logger


class TestPrinter(TestCase):
    def setUp(self):
        self.tmtc_printer = TmTcPrinter()
        self.logger = get_logger()
        set_tmtc_logger()

    def test_print_functions(self):
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.LONG)
        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.SHORT)
        self.tmtc_printer.set_display_mode(DisplayMode.LONG)

        service_1_packed = Service1TmPacked(subservice=1)
        service_1_tm = Service1TM(service_1_packed.pack())
        self.tmtc_printer.print_telemetry(packet=service_1_tm)
        # Should not crash and emit warning
        self.tmtc_printer.print_telemetry(packet=None)

        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.tmtc_printer.print_telemetry(packet=service_1_tm)
        service_1_packed = Service1TmPacked(subservice=2)
        service_1_tm = Service1TM(service_1_packed.pack())
        self.tmtc_printer.print_telemetry(packet=service_1_tm, print_raw_tm=True)

        self.tmtc_printer.set_display_mode(DisplayMode.LONG)
