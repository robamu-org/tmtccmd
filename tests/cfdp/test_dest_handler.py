import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

from spacepackets.cfdp import (
    ChecksumType,
    PduConfig,
    TransmissionMode,
)
from spacepackets.util import ByteFieldU16, ByteFieldU8
from tmtccmd.cfdp import (
    IndicationCfg,
    LocalEntityCfg,
    RemoteEntityCfgTable,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import TransactionId
from tmtccmd.cfdp.handler.dest import (
    DestHandler,
)

from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser
from .common import CheckTimerProviderForTest


class TestDestHandlerBase(TestCase):
    def common_setup(self):
        self.indication_cfg = IndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.entity_id = ByteFieldU16(2)
        self.local_cfg = LocalEntityCfg(
            self.entity_id, self.indication_cfg, self.fault_handler
        )
        self.src_entity_id = ByteFieldU16(1)
        self.src_pdu_conf = PduConfig(
            source_entity_id=self.src_entity_id,
            dest_entity_id=self.entity_id,
            transaction_seq_num=ByteFieldU8(1),
            trans_mode=TransmissionMode.UNACKNOWLEDGED,
        )
        self.transaction_id = TransactionId(self.src_entity_id, ByteFieldU8(1))
        self.closure_requested = False
        self.cfdp_user = CfdpUser()
        self.file_segment_len = 128
        self.cfdp_user.eof_recv_indication = MagicMock()
        self.cfdp_user.file_segment_recv_indication = MagicMock()
        self.cfdp_user.transaction_finished_indication = MagicMock()
        self.src_file_path = Path(f"{tempfile.gettempdir()}/hello.txt")
        if self.src_file_path.exists():
            os.remove(self.src_file_path)
        self.dest_file_path = Path(f"{tempfile.gettempdir()}/hello_dest.txt")
        if self.dest_file_path.exists():
            os.remove(self.dest_file_path)
        self.remote_cfg_table = RemoteEntityCfgTable()
        self.remote_cfg = RemoteEntityCfg(
            entity_id=self.src_entity_id,
            check_limit=2,
            crc_type=ChecksumType.CRC_32,
            closure_requested=False,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionMode.UNACKNOWLEDGED,
            max_file_segment_len=self.file_segment_len,
            max_packet_len=self.file_segment_len,
        )
        self.remote_cfg_table.add_config(self.remote_cfg)
        self.timeout_check_limit_handling_ms = 30
        self.dest_handler = DestHandler(
            self.local_cfg,
            self.cfdp_user,
            self.remote_cfg_table,
            CheckTimerProviderForTest(
                timeout_dest_entity_ms=self.timeout_check_limit_handling_ms
            ),
        )
