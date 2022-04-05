import shutil
import os
from unittest import TestCase

from tmtccmd.runner import init_tmtccmd
from tmtccmd.tm import Service5Tm
from tmtccmd.pus.service_1_verification import Service1TMExtended
from tmtccmd.tm.service_5_event import Srv5Subservices
from spacepackets.ccsds.time import CdsShortTimestamp
from tmtccmd.pus.service_17_test import pack_service_17_ping_command
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter, DisplayMode
from tmtccmd.logging import get_console_logger, LOG_DIR
from tmtccmd.config.globals import update_global, CoreGlobalIds
from tmtccmd.logging.pus import (
    log_raw_pus_tc,
    log_raw_pus_tm,
    get_current_raw_file_name,
    create_tmtc_logger
)

from tests.hook_obj_mock import create_hook_mock_with_srv_handlers


class TestPrintersLoggers(TestCase):
    def setUp(self):
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)
        os.mkdir(LOG_DIR)
        self.tmtc_printer = FsfwTmTcPrinter(file_logger=create_tmtc_logger())
        self.logger = get_console_logger()

    def test_pus_loggers(self):
        pus_tc = pack_service_17_ping_command(ssc=0)
        file_name = get_current_raw_file_name()
        log_raw_pus_tc(pus_tc.pack())
        pus_tm = Service1TMExtended(
            subservice=1, time=CdsShortTimestamp.init_from_current_time()
        )
        log_raw_pus_tm(pus_tm.pack())
        log_raw_pus_tc(
            pus_tc.pack(), srv_subservice=(pus_tc.service, pus_tc.subservice)
        )
        log_raw_pus_tm(
            pus_tm.pack(), srv_subservice=(pus_tm.service, pus_tm.subservice)
        )
        self.assertTrue(os.path.exists(file_name))

    def test_print_functions(self):
        self.assertTrue(self.tmtc_printer.display_mode == DisplayMode.LONG)
        self.tmtc_printer.display_mode = DisplayMode.SHORT
        self.assertTrue(self.tmtc_printer.display_mode == DisplayMode.SHORT)
        self.tmtc_printer.display_mode = DisplayMode.LONG

        service_1_tm = Service1TMExtended(
            subservice=1, time=CdsShortTimestamp.init_from_current_time()
        )
        service_1_packed = service_1_tm.pack()
        # TODO: Fix these tests
        # self.tmtc_printer.print_telemetry(packet_if=service_1_tm, info_if=service_1_tm)
        # Should not crash and emit warning
        self.tmtc_printer.print_telemetry(packet_if=None, info_if=None)

        self.tmtc_printer.display_mode = DisplayMode.SHORT
        self.tmtc_printer.print_telemetry(packet_if=service_1_tm, info_if=service_1_tm)
        service_1_tm = Service1TMExtended(
            subservice=2, time=CdsShortTimestamp.init_from_current_time()
        )
        service_1_packed = service_1_tm.pack()
        self.tmtc_printer.print_telemetry(
            packet_if=service_1_tm, info_if=service_1_tm, print_raw_tm=True
        )

        self.tmtc_printer.display_mode = DisplayMode.LONG
        service_5_tm = Service5Tm(
            subservice=Srv5Subservices.INFO_EVENT,
            object_id=bytearray([0x01, 0x02, 0x03, 0x04]),
            event_id=22,
            param_1=32,
            param_2=82452,
            time=CdsShortTimestamp.init_from_current_time(),
        )
        hook_base = create_hook_mock_with_srv_handlers()
        init_tmtccmd(hook_object=hook_base)

        service_5_packed = service_5_tm.pack()
        self.tmtc_printer.print_telemetry(packet_if=service_5_tm, info_if=service_5_tm)

        # Fix this test
        """
        hook_base.handle_service_5_event.assert_called_with(
            object_id=bytes([0x01, 0x02, 0x03, 0x04]),
            event_id=22,
            param_1=32,
            param_2=82452,
        )
        """


        service_17_command = pack_service_17_ping_command(ssc=0, apid=42)
        self.tmtc_printer.print_telecommand(
            tc_packet_obj=service_17_command, tc_packet_raw=service_17_command.pack()
        )
        self.tmtc_printer.display_mode = DisplayMode.SHORT
        self.tmtc_printer.print_telecommand(
            tc_packet_obj=service_17_command, tc_packet_raw=service_17_command.pack()
        )
        self.tmtc_printer.display_mode = DisplayMode.LONG

    def tearDown(self) -> None:
        """Reset the hook object"""
        update_global(CoreGlobalIds.TMTC_HOOK, None)
        shutil.rmtree(LOG_DIR)
