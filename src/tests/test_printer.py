from unittest import TestCase

from tmtccmd.runner import initialize_tmtc_commander
from tmtccmd.tm import Service1TM, Service5TM, Srv5Subservices, CdsShortTimestamp
from tmtccmd.tc.service_17_test import pack_service17_ping_command
from tmtccmd.utility.tmtc_printer import TmTcPrinter, DisplayMode
from tmtccmd.utility.logger import get_console_logger, set_tmtc_console_logger
from tmtccmd.config.globals import update_global, CoreGlobalIds

from .hook_obj_mock import create_hook_mock_with_srv_handlers


class TestPrinter(TestCase):

    def setUp(self):
        self.tmtc_printer = TmTcPrinter()
        self.logger = get_console_logger()
        set_tmtc_console_logger()

    def test_print_functions(self):
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.LONG)
        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.assertTrue(self.tmtc_printer.get_display_mode() == DisplayMode.SHORT)
        self.tmtc_printer.set_display_mode(DisplayMode.LONG)

        service_1_tm = Service1TM(subservice_id=1, time=CdsShortTimestamp.init_from_current_time())
        service_1_packed = service_1_tm.pack()
        self.tmtc_printer.print_telemetry(packet_if=service_1_tm, info_if=service_1_tm)
        # Should not crash and emit warning
        self.tmtc_printer.print_telemetry(packet_if=None, info_if=None)

        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.tmtc_printer.print_telemetry(packet_if=service_1_tm, info_if=service_1_tm)
        service_1_tm = Service1TM(subservice_id=2, time=CdsShortTimestamp.init_from_current_time())
        service_1_packed = service_1_tm.pack()
        self.tmtc_printer.print_telemetry(
            packet_if=service_1_tm, info_if=service_1_tm, print_raw_tm=True
        )

        self.tmtc_printer.set_display_mode(DisplayMode.LONG)
        service_5_tm = Service5TM(
            subservice_id=Srv5Subservices.INFO_EVENT, object_id=bytearray([0x01, 0x02, 0x03, 0x04]),
            event_id=22, param_1=32, param_2=82452, time=CdsShortTimestamp.init_from_current_time()
        )
        hook_base = create_hook_mock_with_srv_handlers()
        initialize_tmtc_commander(hook_object=hook_base)

        service_5_packed = service_5_tm.pack()
        self.tmtc_printer.print_telemetry(packet_if=service_5_tm, info_if=service_5_tm)

        hook_base.handle_service_5_event.assert_called_with(
            object_id=bytes([0x01, 0x02, 0x03, 0x04]), event_id=22, param_1=32, param_2=82452
        )

        service_17_command = pack_service17_ping_command(ssc=0, apid=42)
        self.tmtc_printer.print_telecommand(
            tc_packet_obj=service_17_command, tc_packet_raw=service_17_command.pack()
        )
        self.tmtc_printer.set_display_mode(DisplayMode.SHORT)
        self.tmtc_printer.print_telecommand(
            tc_packet_obj=service_17_command, tc_packet_raw=service_17_command.pack()
        )
        self.tmtc_printer.set_display_mode(DisplayMode.LONG)

        self.tmtc_printer.clear_file_buffer()

    def tearDown(self) -> None:
        """Reset the hook object"""
        update_global(CoreGlobalIds.TMTC_HOOK, None)
