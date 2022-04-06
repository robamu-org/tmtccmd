import shutil
import os
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp

from tmtccmd.pus.service_1_verification import Service1TMExtended
from tmtccmd.pus.service_17_test import pack_service_17_ping_command
from tmtccmd.utility.tmtc_printer import FsfwTmTcPrinter
from tmtccmd.logging import get_console_logger, LOG_DIR
from tmtccmd.config.globals import update_global, CoreGlobalIds
from tmtccmd.logging.pus import (
    log_raw_pus_tc,
    log_raw_pus_tm,
    get_current_raw_file_name,
    create_tmtc_logger,
)


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
        pass

    def tearDown(self) -> None:
        """Reset the hook object"""
        update_global(CoreGlobalIds.TMTC_HOOK, None)
        if os.path.exists(LOG_DIR):
            shutil.rmtree(LOG_DIR)
