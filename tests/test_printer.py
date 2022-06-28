import os
import shutil
from pathlib import Path
from tempfile import TemporaryFile
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_1_verification import RequestId

from tmtccmd.tm.pus_1_verification import Service1TmExtended
from tmtccmd.pus.pus_17_test import pack_service_17_ping_command
from tmtccmd.logging import get_console_logger, LOG_DIR
from tmtccmd.config.globals import update_global, CoreGlobalIds
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcRotatingLogWrapper,
)


# TODO: Use temp files to test loggers?gitas
class TestPrintersLoggers(TestCase):
    def setUp(self):
        self.log_path = Path(LOG_DIR)
        if not self.log_path.exists():
            self.log_path.mkdir()
        self.regular_file_name = Path(RegularTmtcLogWrapper.get_current_tmtc_file_name())
        self.logger = get_console_logger()

    def test_pus_loggers(self):
        self.regular_tmtc_logger = RegularTmtcLogWrapper(self.regular_file_name)
        self.raw_tmtc_log = RawTmtcRotatingLogWrapper(max_bytes=2048, backup_count=10)
        pus_tc = pack_service_17_ping_command(ssc=0)
        self.raw_tmtc_log.log_tc(pus_tc)
        pus_tm = Service1TmExtended(
            subservice=1,
            time=CdsShortTimestamp.init_from_current_time(),
            tc_request_id=RequestId(pus_tc.packet_id, pus_tc.packet_seq_ctrl),
        )
        self.raw_tmtc_log.log_tm(pus_tm.pus_tm)
        self.assertTrue(Path(self.regular_file_name).exists())
        # There should be 2 files now because 1024 bytes are not enough to accomate all info
        self.assertTrue(Path(self.raw_tmtc_log.file_name).exists())
        self.assertTrue(Path(f"{self.raw_tmtc_log.file_name}.1").exists())

    def test_print_functions(self):
        pass

    def tearDown(self) -> None:
        """Reset the hook object"""
        # if self.regular_file_name.exists():
            # os.remove(self.regular_file_name)
