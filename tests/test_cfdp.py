from pathlib import Path
from typing import Optional, List
from unittest import TestCase

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv
from spacepackets.cfdp.defs import ByteFieldU16, FaultHandlerCodes, TransmissionModes
from spacepackets.cfdp.pdu.finished import FileDeliveryStatus, DeliveryCode
from tmtccmd.cfdp import CfdpUserBase
from tmtccmd.cfdp.defs import TransactionId
from tmtccmd.cfdp.handler import CfdpSourceHandler
from tmtccmd.cfdp.mib import (
    LocalEntityCfg,
    LocalIndicationCfg,
    DefaultFaultHandlerBase,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.request import CfdpRequestWrapper, PutRequest, PutRequestCfg
from tmtccmd.util.seqcnt import SeqCountProvider


class FaultHandler(DefaultFaultHandlerBase):
    def __init__(self):
        self.was_called = False
        self.call_count = 0

    def handle_fault(self, code: FaultHandlerCodes):
        self.was_called = True
        self.call_count += 1


class CfdpUser(CfdpUserBase):
    def transaction_indication(self, transaction_id: TransactionId):
        pass

    def transaction_finished_indication(
        self,
        transaction_id: TransactionId,
        condition_code: ConditionCode,
        file_status: FileDeliveryStatus,
        delivery_code: DeliveryCode,
        _fs_responses: Optional[List[FileStoreResponseTlv]] = None,
        _status_report: Optional[any] = None,
    ):
        pass

    def eof_sent_indication(self, transaction_id: TransactionId):
        pass

    def abandon_indication(
        self, transaction_id: int, cond_code: ConditionCode, progress: int
    ):
        pass


class TestCfdp(TestCase):
    def setUp(self) -> None:
        self.indication_cfg = LocalIndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.local_cfg = LocalEntityCfg(
            ByteFieldU16(1), self.indication_cfg, self.fault_handler
        )
        self.cfdp_user = CfdpUser()
        self.seq_num_provider = SeqCountProvider(bit_width=8)
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        self.remote_cfg = RemoteEntityCfg(
            remote_entity_id=self.dest_id,
            max_file_segment_len=256,
            closure_requested=False,
            crc_on_transmission=False,
        )

    def test_source_handler(self):
        # Create an empty file and send it via CFDP
        source_handler = CfdpSourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )
        file_path = Path("hello.txt")
        with open(file_path):
            pass
        put_req_cfg = PutRequestCfg(
            destination_id=ByteFieldU16(2),
            source_file=file_path,
            dest_file="/tmp/hello.txt",
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
            closure_requested=False,
        )
        wrapper = CfdpRequestWrapper(PutRequest(put_req_cfg))
        source_handler.start_transaction(wrapper, self.remote_cfg)
        pass

    pass
