import os
import random
import tempfile
from crcmod.predefined import PredefinedCrc
from pathlib import Path
from typing import Optional, List
from unittest import TestCase

from spacepackets.cfdp import ConditionCode, FileStoreResponseTlv
from spacepackets.cfdp.defs import (
    FaultHandlerCodes,
    TransmissionModes,
    ChecksumTypes,
    NULL_CHECKSUM_U32,
    PduType,
)
from spacepackets.cfdp.pdu import DirectiveType
from spacepackets.cfdp.pdu.file_data import FileDataPdu
from spacepackets.cfdp.pdu.finished import FileDeliveryStatus, DeliveryCode
from spacepackets.util import ByteFieldU16, ByteFieldU32, UnsignedByteField, ByteFieldU8
from tmtccmd.cfdp import CfdpUserBase
from tmtccmd.cfdp.defs import TransactionId, CfdpStates, SourceTransactionStep
from tmtccmd.cfdp.handler import CfdpSourceHandler, FsmResult, PacketSendNotConfirmed
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
    def __init__(self):
        super().__init__()
        self.transaction_inidcation_was_called = False
        self.transaction_inidcation_call_count = 0
        self.transaction_finished_was_called = False
        self.transaction_finished_call_count = 0
        self.eof_sent_indication_was_called = False
        self.eof_sent_indication_call_count = 0

    def transaction_indication(self, transaction_id: TransactionId):
        self.transaction_inidcation_was_called = True
        self.transaction_inidcation_call_count += 1

    def transaction_finished_indication(
        self,
        transaction_id: TransactionId,
        condition_code: ConditionCode,
        file_status: FileDeliveryStatus,
        delivery_code: DeliveryCode,
        _fs_responses: Optional[List[FileStoreResponseTlv]] = None,
        _status_report: Optional[any] = None,
    ):
        self.transaction_finished_was_called = True
        self.transaction_finished_call_count += 1

    def eof_sent_indication(self, transaction_id: TransactionId):
        self.eof_sent_indication_was_called = True
        self.eof_sent_indication_call_count += 1

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
        self.file_path = Path(f"{tempfile.gettempdir()}/hello.txt")
        with open(self.file_path, "w"):
            pass
        self.file_segment_len = 256
        self.remote_cfg = RemoteEntityCfg(
            remote_entity_id=self.dest_id,
            max_file_segment_len=self.file_segment_len,
            closure_requested=False,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionModes.UNACKNOWLEDGED,
        )

    def test_source_handler_empty_file(self):
        dest_path = "/tmp/hello_copy.txt"
        dest_id = ByteFieldU16(2)
        put_req_cfg = PutRequestCfg(
            destination_id=dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        source_handler = self._start_source_transaction(
            dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        self.assertTrue(fsm_res.pdu_holder.is_file_directive)
        self.assertEqual(fsm_res.pdu_holder.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(eof_pdu.file_checksum, NULL_CHECKSUM_U32)
        self.assertEqual(eof_pdu.file_size, 0)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        self.assertEqual(eof_pdu.fault_location, None)
        # This indication will be called if the EOF send was confirmed
        self.assertFalse(self.cfdp_user.eof_sent_indication_was_called)
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertTrue(self.cfdp_user.eof_sent_indication_was_called)
        self.assertEqual(self.cfdp_user.eof_sent_indication_call_count, 1)
        fsm_res = source_handler.state_machine()
        self.assertTrue(self.cfdp_user.transaction_finished_was_called)
        self.assertEqual(self.cfdp_user.transaction_finished_call_count, 1)
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)

    def test_source_handler_small_file(self):
        dest_path = "/tmp/hello_copy.txt"
        self.source_id = ByteFieldU32(1)
        self.dest_id = ByteFieldU32(2)
        put_req_cfg = PutRequestCfg(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            data = "Hello World\n".encode()
            crc32.update(data)
            crc32 = crc32.digest()
            of.write(data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        source_handler = self._start_source_transaction(
            self.dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        file_data_pdu = self._check_file_data(fsm_res)
        self.assertFalse(file_data_pdu.has_segment_metadata)
        self.assertEqual(file_data_pdu.file_data, "Hello World\n".encode())
        self.assertEqual(file_data_pdu.offset, 0)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        self.assertEqual(fsm_res.pdu_holder.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(crc32, eof_pdu.file_checksum)
        self.assertEqual(eof_pdu.file_size, file_size)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        with self.assertRaises(PacketSendNotConfirmed):
            source_handler.state_machine()
        self._test_transaction_completion(source_handler)

    def test_source_handler_perfectly_segmented_file(self):
        # This tests generates two file data PDUs
        rand_data = random.randbytes(self.file_segment_len * 2)
        self.source_id = ByteFieldU8(1)
        self.dest_id = ByteFieldU8(2)
        dest_path = "/tmp/hello_two_segments_copy.txt"
        put_req_cfg = PutRequestCfg(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            crc32.update(rand_data)
            crc32 = crc32.digest()
            of.write(rand_data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        source_handler = self._start_source_transaction(
            self.dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        file_data_pdu = self._check_file_data(fsm_res)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            rand_data[0 : self.file_segment_len],
        )
        self.assertEqual(file_data_pdu.offset, 0)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        file_data_pdu = fsm_res.pdu_holder.to_file_data_pdu()
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(source_handler)

    def test_source_handler_segmented_file(self):
        # This tests generates two file data PDUs, but the second one does not have a
        # full segment length
        rand_data = random.randbytes(round(self.file_segment_len * 1.5))
        remainder_len = len(rand_data) - self.file_segment_len
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        dest_path = "/tmp/hello_two_segments_imperfect_copy.txt"
        put_req_cfg = PutRequestCfg(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            crc32.update(rand_data)
            crc32 = crc32.digest()
            of.write(rand_data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        source_handler = self._start_source_transaction(
            self.dest_id, PutRequest(put_req_cfg)
        )
        fsm_res = source_handler.state_machine()
        file_data_pdu = self._check_file_data(fsm_res)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            rand_data[0 : self.file_segment_len],
        )
        self.assertEqual(file_data_pdu.offset, 0)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        file_data_pdu = fsm_res.pdu_holder.to_file_data_pdu()
        self.assertEqual(len(file_data_pdu.file_data), remainder_len)
        self.assertEqual(
            file_data_pdu.file_data[:],
            rand_data[self.file_segment_len :],
        )
        self.assertEqual(file_data_pdu.offset, self.file_segment_len)
        source_handler.confirm_packet_sent_advance_fsm()
        fsm_res = source_handler.state_machine()
        self._test_eof_file_pdu(fsm_res, file_size, crc32)
        self._test_transaction_completion(source_handler)

    def _check_file_data(self, fsm_res: FsmResult) -> FileDataPdu:
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_FILE_DATA)
        self.assertFalse(fsm_res.pdu_holder.is_file_directive)
        return fsm_res.pdu_holder.to_file_data_pdu()

    def _test_eof_file_pdu(self, fsm_res: FsmResult, file_size: int, crc32: bytes):
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_EOF)
        eof_pdu = fsm_res.pdu_holder.to_eof_pdu()
        self.assertEqual(eof_pdu.file_size, file_size)
        self.assertEqual(eof_pdu.file_checksum, crc32)

    def _test_transaction_completion(self, source_handler: CfdpSourceHandler):
        source_handler.confirm_packet_sent_advance_fsm()
        self.assertTrue(self.cfdp_user.eof_sent_indication_was_called)
        self.assertEqual(self.cfdp_user.eof_sent_indication_call_count, 1)
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.IDLE)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.IDLE)
        self.assertTrue(self.cfdp_user.transaction_finished_was_called)
        self.assertEqual(self.cfdp_user.transaction_finished_call_count, 1)

    def _start_source_transaction(
        self, dest_id: UnsignedByteField, put_request: PutRequest
    ) -> CfdpSourceHandler:
        # Create an empty file and send it via CFDP
        source_handler = CfdpSourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )

        wrapper = CfdpRequestWrapper(put_request)
        source_handler.start_transaction(wrapper, self.remote_cfg)
        fsm_res = source_handler.state_machine()
        self.assertEqual(fsm_res.states.state, CfdpStates.BUSY_CLASS_1_NACKED)
        self.assertEqual(fsm_res.states.step, SourceTransactionStep.SENDING_METADATA)
        self.assertTrue(self.cfdp_user.transaction_inidcation_was_called)
        self.assertEqual(self.cfdp_user.transaction_inidcation_call_count, 1)
        self.assertTrue(fsm_res.pdu_holder.is_file_directive)
        self.assertEqual(
            fsm_res.pdu_holder.pdu_directive_type, DirectiveType.METADATA_PDU
        )
        metadata_pdu = fsm_res.pdu_holder.to_metadata_pdu()
        if put_request.cfg.closure_requested is not None:
            self.assertEqual(
                metadata_pdu.params.closure_requested, put_request.cfg.closure_requested
            )
        self.assertEqual(metadata_pdu.checksum_type, ChecksumTypes.CRC_32)
        self.assertEqual(metadata_pdu.source_file_name, self.file_path.as_posix())
        self.assertEqual(metadata_pdu.dest_file_name, put_request.cfg.dest_file)
        self.assertEqual(metadata_pdu.dest_entity_id, dest_id)
        source_handler.confirm_packet_sent_advance_fsm()
        return source_handler

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
