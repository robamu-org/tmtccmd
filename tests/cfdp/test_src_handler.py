import os
import tempfile
from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import TransmissionModes
from spacepackets.util import ByteFieldU16
from tmtccmd.cfdp import LocalIndicationCfg, LocalEntityCfg, RemoteEntityCfg
from tmtccmd.cfdp.handler import CfdpSourceHandler
from tmtccmd.util import SeqCountProvider
from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser


class TestCfdpSourceHandler(TestCase):
    def common_setup(self, closure_requested: bool):
        self.indication_cfg = LocalIndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.local_cfg = LocalEntityCfg(
            ByteFieldU16(1), self.indication_cfg, self.fault_handler
        )
        self.cfdp_user = CfdpUser()
        self.seq_num_provider = SeqCountProvider(bit_width=8)
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        self.file_path = Path(f"{tempfile.gettempdir()}/hello.txt")
        with open(self.file_path, "w"):
            pass
        self.file_segment_len = 256
        self.remote_cfg = RemoteEntityCfg(
            remote_entity_id=self.dest_id,
            max_file_segment_len=self.file_segment_len,
            closure_requested=closure_requested,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionModes.UNACKNOWLEDGED,
        )
        # Create an empty file and send it via CFDP
        self.source_handler = CfdpSourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
