from unittest import TestCase
from tmtccmd.utility.tmtc_printer import TmTcPrinter, DisplayMode

class TestPrinter(TestCase):
    def setUp(self):
        self.tmtc_printer = TmTcPrinter()

    def test_print_functions(self):
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.LONG)
        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.SHORT)
        self.tmtc_printer.set_display_mode(DisplayMode.LONG)
