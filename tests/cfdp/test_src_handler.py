import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from unittest import TestCase
from unittest.mock import MagicMock

from crcmod.predefined import PredefinedCrc

from spacepackets.cfdp import (
    PduHolder,
    PduType,
    TransmissionMode,
    NULL_CHECKSUM_U32,
    ConditionCode,
    ChecksumType,
)
from spacepackets.cfdp.pdu import DirectiveType, FileDataPdu
from spacepackets.util import ByteFieldU16, UnsignedByteField, ByteFieldU32
from tmtccmd.cfdp import IndicationCfg, LocalEntityCfg, RemoteEntityCfg
from tmtccmd.cfdp.defs import CfdpState, TransactionId
from tmtccmd.cfdp.handler import SourceHandler, FsmResult
from tmtccmd.cfdp.handler.defs import UnretrievedPdusToBeSent
from tmtccmd.cfdp.handler.source import TransactionStep
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.util import SeqCountProvider
from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser


class TestCfdpSourceHandler(TestCase):
    """It should be noted that this only verifies the correct generation of PDUs. There is
    no reception handler in play here which would be responsible for generating the files
    from these PDUs
    """

    def common_setup(
        self, closure_requested: bool, default_transmission_mode: TransmissionMode
    ):
        self.indication_cfg = IndicationCfg(True, True, True, True, True, True)
        self.fault_handler = FaultHandler()
        self.local_cfg = LocalEntityCfg(
            ByteFieldU16(1), self.indication_cfg, self.fault_handler
        )
        self.cfdp_user = CfdpUser()
        self.cfdp_user.eof_sent_indication = MagicMock()
        self.cfdp_user.transaction_indication = MagicMock()
        self.cfdp_user.transaction_finished_indication = MagicMock()
        self.seq_num_provider = SeqCountProvider(bit_width=8)
        self.source_id = ByteFieldU16(1)
        self.dest_id = ByteFieldU16(2)
        self.file_path = Path(f"{tempfile.gettempdir()}/hello.txt")
        if self.file_path.exists():
            os.remove(self.file_path)
        with open(self.file_path, "w"):
            pass
        self.file_segment_len = 256
        self.remote_cfg = RemoteEntityCfg(
            entity_id=self.dest_id,
            max_file_segment_len=self.file_segment_len,
            closure_requested=closure_requested,
            crc_on_transmission=False,
            default_transmission_mode=default_transmission_mode,
            crc_type=ChecksumType.CRC_32,
            check_limit_provider=None,
        )
        # Create an empty file and send it via CFDP
        self.source_handler = SourceHandler(
            self.local_cfg, self.seq_num_provider, self.cfdp_user
        )

    def _common_empty_file_test(
        self, transmission_mode: Optional[TransmissionMode], expected_state: CfdpState
    ):
        dest_path = Path("/tmp/hello_copy.txt")
        dest_id = ByteFieldU16(2)
        self.seq_num_provider.get_and_increment = MagicMock(return_value=3)
        put_req = PutRequest(
            destination_id=dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=transmission_mode,
            closure_requested=None,
        )
        transaction_id = self._start_source_transaction(
            dest_id, put_req, expected_state
        )
        fsm_res = self.source_handler.state_machine()
        self._state_checker(fsm_res, True, expected_state, TransactionStep.SENDING_EOF)
        self.assertEqual(self.source_handler.transaction_seq_num.value, 3)
        next_packet = self.source_handler.get_next_packet()
        self.assertIsNotNone(next_packet)
        assert next_packet is not None
        self.assertEqual(next_packet.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_packet.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = next_packet.to_eof_pdu()
        self.assertEqual(eof_pdu.transaction_seq_num.value, 3)
        # For an empty file, checksum verification does not really make sense, so we expect
        # a null checksum here.
        self.assertEqual(eof_pdu.file_checksum, NULL_CHECKSUM_U32)
        self.assertEqual(eof_pdu.file_size, 0)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        self.assertEqual(eof_pdu.fault_location, None)
        fsm_res = self.source_handler.state_machine()
        self._verify_eof_indication(transaction_id)

    def _common_small_file_test(
        self, closure_requested: bool, file_content: str, expected_state: CfdpState
    ) -> TransactionId:
        dest_path = Path("/tmp/hello_copy.txt")
        self.source_id = ByteFieldU32(1)
        self.dest_id = ByteFieldU32(2)
        self.seq_num_provider.get_and_increment = MagicMock(return_value=2)
        self.source_handler.source_id = self.source_id
        put_req = PutRequest(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=closure_requested,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            data = file_content.encode()
            crc32.update(data)
            crc32 = crc32.digest()
            of.write(data)
        file_size = self.file_path.stat().st_size
        transaction_id = self._start_source_transaction(
            self.dest_id, put_req, expected_state
        )
        self.assertEqual(transaction_id.source_id, self.source_handler.source_id)
        self.assertEqual(transaction_id.seq_num.value, 2)
        self.assertEqual(self.source_handler.transaction_seq_num.value, 2)
        fsm_res = self.source_handler.state_machine()
        with self.assertRaises(UnretrievedPdusToBeSent):
            self.source_handler.state_machine()
        next_packet = self.source_handler.get_next_packet()
        assert next_packet is not None
        file_data_pdu = self._check_fsm_and_contained_file_data(fsm_res, next_packet)
        self.assertFalse(file_data_pdu.has_segment_metadata)
        self.assertEqual(file_data_pdu.transaction_seq_num.value, 2)
        self.assertEqual(file_data_pdu.file_data, "Hello World\n".encode())
        self.assertEqual(file_data_pdu.offset, 0)
        fsm_res = self.source_handler.state_machine()
        self._state_checker(
            fsm_res, True, CfdpState.BUSY_CLASS_1_NACKED, TransactionStep.SENDING_EOF
        )
        next_packet = self.source_handler.get_next_packet()
        assert next_packet is not None
        self.assertEqual(next_packet.pdu_directive_type, DirectiveType.EOF_PDU)
        eof_pdu = next_packet.to_eof_pdu()
        self.assertEqual(crc32, eof_pdu.file_checksum)
        self.assertEqual(eof_pdu.file_size, file_size)
        self.assertEqual(eof_pdu.condition_code, ConditionCode.NO_ERROR)
        return transaction_id

    def _transaction_with_file_data_wrapper(
        self, dest_path: Path, data: bytes, expected_state: CfdpState
    ) -> Tuple[TransactionId, int, bytes]:
        put_req = PutRequest(
            destination_id=self.dest_id,
            source_file=self.file_path,
            dest_file=dest_path,
            # Let the transmission mode be auto-determined by the remote MIB
            trans_mode=None,
            closure_requested=False,
        )
        with open(self.file_path, "wb") as of:
            crc32 = PredefinedCrc("crc32")
            crc32.update(data)
            crc32 = crc32.digest()
            of.write(data)
        file_size = self.file_path.stat().st_size
        self.local_cfg.local_entity_id = self.source_id
        transaction_id = self._start_source_transaction(
            self.dest_id, put_req, expected_state
        )
        return transaction_id, file_size, crc32

    def _first_file_segment_handling(
        self, source_handler: SourceHandler, all_data: bytes
    ):
        fsm_res = source_handler.state_machine()
        next_packet = source_handler.get_next_packet()
        assert next_packet is not None
        file_data_pdu = self._check_fsm_and_contained_file_data(fsm_res, next_packet)
        self.assertEqual(len(file_data_pdu.file_data), self.file_segment_len)
        self.assertEqual(
            file_data_pdu.file_data[0 : self.file_segment_len],
            all_data[0 : self.file_segment_len],
        )
        self.assertEqual(file_data_pdu.offset, 0)
        next_packet = source_handler.get_next_packet()
        assert next_packet is None

    def _check_fsm_and_contained_file_data(
        self, fsm_res: FsmResult, pdu_holder: PduHolder
    ) -> FileDataPdu:
        self._state_checker(
            fsm_res,
            False,
            CfdpState.BUSY_CLASS_1_NACKED,
            TransactionStep.SENDING_FILE_DATA,
        )
        self.assertFalse(pdu_holder.is_file_directive)
        return pdu_holder.to_file_data_pdu()

    def _start_source_transaction(
        self,
        dest_id: UnsignedByteField,
        put_request: PutRequest,
        expected_state: CfdpState,
    ) -> TransactionId:
        self.remote_cfg.entity_id = dest_id
        self.source_handler.put_request(put_request, self.remote_cfg)
        fsm_res = self.source_handler.state_machine()
        self._state_checker(
            fsm_res,
            True,
            expected_state,
            TransactionStep.SENDING_METADATA,
        )
        transaction_id = self.source_handler.transaction_id
        assert transaction_id is not None
        self.cfdp_user.transaction_indication.assert_called_once()
        self.assertEqual(self.cfdp_user.transaction_indication.call_count, 1)
        next_packet = self.source_handler.get_next_packet()
        assert next_packet is not None
        self.assertEqual(next_packet.pdu_type, PduType.FILE_DIRECTIVE)
        self.assertEqual(next_packet.pdu_directive_type, DirectiveType.METADATA_PDU)
        metadata_pdu = next_packet.to_metadata_pdu()
        if put_request.closure_requested is not None:
            self.assertEqual(
                metadata_pdu.params.closure_requested, put_request.closure_requested
            )
        self.assertEqual(metadata_pdu.checksum_type, ChecksumType.CRC_32)
        self.assertEqual(metadata_pdu.source_file_name, self.file_path.as_posix())
        assert put_request.dest_file is not None
        self.assertEqual(metadata_pdu.dest_file_name, put_request.dest_file.as_posix())
        self.assertEqual(metadata_pdu.dest_entity_id, dest_id)
        return transaction_id

    def _verify_eof_indication(self, expected_transaction_id: TransactionId):
        self.source_handler.state_machine()
        self.cfdp_user.eof_sent_indication.assert_called_once()
        self.assertEqual(self.cfdp_user.eof_sent_indication.call_count, 1)
        self.assertIsNotNone(
            self.cfdp_user.eof_sent_indication.call_args[0], expected_transaction_id
        )

    def _state_checker(
        self,
        fsm_res: Optional[FsmResult],
        packet_ready: bool,
        expected_state: CfdpState,
        expected_step: TransactionStep,
    ):
        if fsm_res is not None:
            self.assertEqual(fsm_res.states.state, expected_state)
            self.assertEqual(fsm_res.states.step, expected_step)
        self.assertEqual(self.source_handler.states.state, expected_state)
        self.assertEqual(self.source_handler.states.step, expected_step)
        self.assertEqual(self.source_handler.states.packets_ready, packet_ready)
        self.assertEqual(self.source_handler.state, expected_state)
        self.assertEqual(self.source_handler.step, expected_step)
        self.assertEqual(self.source_handler.packets_ready, packet_ready)

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
