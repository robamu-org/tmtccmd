import os
from pathlib import Path
from typing import Optional, List
from unittest import TestCase

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv
from spacepackets.cfdp.defs import FaultHandlerCodes, TransmissionModes, ChecksumTypes
from spacepackets.cfdp.pdu import DirectiveType
from spacepackets.cfdp.pdu.finished import FileDeliveryStatus, DeliveryCode
from spacepackets.util import ByteFieldU16
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
        self.file_path = Path("/tmp/hello.txt")
        with open(self.file_path, "w"):
            pass
        self.remote_cfg = RemoteEntityCfg(
            remote_entity_id=self.dest_id,
            max_file_segment_len=256,
            closure_requested=False,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionModes.UNACKNOWLEDGED,
        )

    def test_source_handler(self):
        # Create an empty file and send it via CFDP
        source_handler = CfdpSourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )
        dest_path = "/tmp/hello_copy.txt"
        put_req_cfg = PutRequestCfg(
            destination_id=ByteFieldU16(2),
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        wrapper = CfdpRequestWrapper(PutRequest(put_req_cfg))
        source_handler.start_transaction(wrapper, self.remote_cfg)
        fsm_res = source_handler.state_machine()
        self.assertTrue(fsm_res.pdu_wrapper.is_file_directive)
        self.assertEqual(
            fsm_res.pdu_wrapper.pdu_directive_type, DirectiveType.METADATA_PDU
        )
        metadata_pdu = fsm_res.pdu_wrapper.to_metadata_pdu()
        self.assertEqual(metadata_pdu.params.closure_requested, False)
        self.assertEqual(metadata_pdu.checksum_type, ChecksumTypes.CRC_32)
        self.assertEqual(metadata_pdu.source_file_name, self.file_path.as_posix())
        self.assertEqual(metadata_pdu.dest_file_name, dest_path)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertTrue(fsm_res.pdu_wrapper.is_file_directive)
        self.assertEqual(fsm_res.pdu_wrapper.pdu_directive_type, DirectiveType.EOF_PDU)
        pass

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
