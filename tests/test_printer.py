import os
from pathlib import Path
from unittest import TestCase

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.pus_1_verification import (
    RequestId,
    VerificationParams,
    Subservice,
    Service1Tm,
)

from tmtccmd.pus.s17_test import create_service_17_ping_command
from tmtccmd.logging import LOG_DIR
from tmtccmd.logging.pus import (
    RegularTmtcLogWrapper,
    RawTmtcRotatingLogWrapper,
)


# TODO: Use temp files to test loggers?
class TestPrintersLoggers(TestCase):
    def setUp(self):
        self.log_path = Path(LOG_DIR)
        if not self.log_path.exists():
            self.log_path.mkdir()
        self.regular_file_name = Path(
            RegularTmtcLogWrapper.get_current_tmtc_file_name()
        )

    def test_pus_loggers(self):
        regular_tmtc_logger = RegularTmtcLogWrapper(self.regular_file_name)
        raw_tmtc_log = RawTmtcRotatingLogWrapper(max_bytes=1024, backup_count=10)
        pus_tc = create_service_17_ping_command()
        raw_tmtc_log.log_tc(pus_tc)
        pus_tm = Service1Tm(
            subservice=Subservice.TM_START_SUCCESS,
            time_provider=CdsShortTimestamp.from_now(),
            verif_params=VerificationParams(
                req_id=RequestId(pus_tc.packet_id, pus_tc.packet_seq_ctrl)
            ),
        )
        raw_tmtc_log.log_tm(pus_tm.pus_tm)
        self.assertTrue(Path(self.regular_file_name).exists())
        regular_tmtc_logger.logger.info("Test")
        # There should be 2 files now because 1024 bytes are not enough to accomate all info
        self.assertTrue(Path(raw_tmtc_log.file_name).exists())
        self.assertTrue(Path(f"{raw_tmtc_log.file_name}.1").exists())

    def test_print_functions(self):
        pass

    def tearDown(self):
        """Reset the hook object"""
        if self.regular_file_name.exists():
            os.remove(self.regular_file_name)
