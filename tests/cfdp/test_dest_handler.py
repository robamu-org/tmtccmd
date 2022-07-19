import os
import random
import struct
import sys
from crcmod.predefined import mkPredefinedCrcFun
import tempfile
from typing import cast, Optional
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

from spacepackets.cfdp import (
    ChecksumTypes,
    PduConfig,
    TransmissionModes,
    NULL_CHECKSUM_U32,
)
from spacepackets.cfdp.pdu import MetadataPdu, MetadataParams, EofPdu, FileDataPdu
from spacepackets.cfdp.pdu.file_data import FileDataParams
from spacepackets.util import ByteFieldU16, ByteFieldU8
from tmtccmd.cfdp import (
    LocalIndicationCfg,
    LocalEntityCfg,
    RemoteEntityCfgTable,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.defs import CfdpStates, TransactionId
from tmtccmd.cfdp.handler.dest import (
    DestHandler,
    TransactionStep,
    FsmResult,
)
from tmtccmd.cfdp.user import TransactionFinishedParams, FileSegmentRecvParams

from .cfdp_fault_handler_mock import FaultHandler
from .cfdp_user_mock import CfdpUser


class TestCfdpDestHandler(TestCase):
    def setUp(self) -> None:
        self.indication_cfg = LocalIndicationCfg(True, True, True, True, True, True)
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
            trans_mode=TransmissionModes.UNACKNOWLEDGED,
        )
        self.transaction_id = TransactionId(self.src_entity_id, ByteFieldU8(1))
        self.closure_requested = False
        self.cfdp_user = CfdpUser()
        self.file_segment_len = 128
        self.cfdp_user.eof_recv_indication = MagicMock()
        self.cfdp_user.file_segment_recv_indication = MagicMock()
        self.cfdp_user.transaction_finished_indication = MagicMock()
        self.file_path = Path(f"{tempfile.gettempdir()}/hello_dest.txt")
        with open(self.file_path, "w"):
            pass
        self.remote_cfg_table = RemoteEntityCfgTable()
        self.remote_cfg = RemoteEntityCfg(
            entity_id=self.src_entity_id,
            check_limit=None,
            crc_type=ChecksumTypes.CRC_32,
            closure_requested=False,
            crc_on_transmission=False,
            default_transmission_mode=TransmissionModes.UNACKNOWLEDGED,
            max_file_segment_len=self.file_segment_len,
        )
        self.remote_cfg_table.add_remote_entity(self.remote_cfg)
        self.dest_handler = DestHandler(
            self.local_cfg, self.cfdp_user, self.remote_cfg_table
        )

    def test_empty_file_reception(self):
        metadata_params = MetadataParams(
            checksum_type=ChecksumTypes.NULL_CHECKSUM,
            closure_requested=False,
            source_file_name=f"{tempfile.gettempdir()}/hello.txt",
            dest_file_name=self.file_path.as_posix(),
            file_size=0,
        )
        file_transfer_init = MetadataPdu(
            params=metadata_params, pdu_conf=self.src_pdu_conf
        )
        self._state_checker(None, CfdpStates.IDLE, TransactionStep.IDLE)
        self.dest_handler.pass_packet(file_transfer_init)
        fsm_res = self.dest_handler.state_machine()
        self.assertFalse(fsm_res.states.packet_ready)
        self.assertEqual(
            self.dest_handler.states.transaction, TransactionStep.RECEIVING_FILE_DATA
        )
        eof_pdu = EofPdu(
            file_size=0, file_checksum=NULL_CHECKSUM_U32, pdu_conf=self.src_pdu_conf
        )
        self.dest_handler.pass_packet(eof_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(fsm_res, CfdpStates.IDLE, TransactionStep.IDLE)
        self.cfdp_user.eof_recv_indication.assert_called_once()
        self.assertEqual(
            self.cfdp_user.eof_recv_indication.call_args.args[0], self.transaction_id
        )
        self.cfdp_user.transaction_finished_indication.assert_called_once()
        finished_params = cast(
            TransactionFinishedParams,
            self.cfdp_user.transaction_finished_indication.call_args.args[0],
        )
        self.assertEqual(finished_params.transaction_id, self.transaction_id)
        self.assertTrue(self.file_path.exists())
        self.assertEqual(self.file_path.stat().st_size, 0)

    def test_small_file_reception(self):
        src_file = Path(f"{tempfile.gettempdir()}/hello.txt")
        with open(src_file, "w") as of:
            of.write("Hello World\n")
        file_size = src_file.stat().st_size
        self._source_simulator_transfer_init_with_metadata(
            checksum=ChecksumTypes.CRC_32,
            file_size=file_size,
            file_path=src_file.as_posix(),
        )
        with open(src_file, "rb") as rf:
            read_data = rf.read()
        fd_params = FileDataParams(file_data=read_data, offset=0)
        file_data_pdu = FileDataPdu(params=fd_params, pdu_conf=self.src_pdu_conf)
        self.dest_handler.pass_packet(file_data_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, CfdpStates.BUSY_CLASS_1_NACKED, TransactionStep.RECEIVING_FILE_DATA
        )

    def test_larger_file_reception(self):
        # This tests generates two file data PDUs, but the second one does not have a
        # full segment length
        if sys.version_info >= (3, 9):
            rand_data = random.randbytes(round(self.file_segment_len * 1.3))
        else:
            rand_data = os.urandom(round(self.file_segment_len * 1.3))
        file_size = len(rand_data)
        crc32_func = mkPredefinedCrcFun("crc32")
        crc32 = struct.pack("!I", crc32_func(rand_data))
        src_file = Path(f"{tempfile.gettempdir()}/hello.txt")
        self._state_checker(None, CfdpStates.IDLE, TransactionStep.IDLE)
        self._source_simulator_transfer_init_with_metadata(
            checksum=ChecksumTypes.CRC_32,
            file_size=file_size,
            file_path=src_file.as_posix(),
        )
        fd_params = FileDataParams(
            file_data=rand_data[0 : self.file_segment_len], offset=0
        )
        file_data_pdu = FileDataPdu(params=fd_params, pdu_conf=self.src_pdu_conf)
        self.dest_handler.pass_packet(file_data_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, CfdpStates.BUSY_CLASS_1_NACKED, TransactionStep.RECEIVING_FILE_DATA
        )
        self.cfdp_user.file_segment_recv_indication.assert_called_once()
        seg_recv_params = cast(
            FileSegmentRecvParams,
            self.cfdp_user.file_segment_recv_indication.call_args.args[0],
        )
        self.assertEqual(seg_recv_params.transaction_id, self.transaction_id)
        fd_params = FileDataParams(
            file_data=rand_data[self.file_segment_len :], offset=self.file_segment_len
        )
        file_data_pdu = FileDataPdu(params=fd_params, pdu_conf=self.src_pdu_conf)
        self.dest_handler.pass_packet(file_data_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(
            fsm_res, CfdpStates.BUSY_CLASS_1_NACKED, TransactionStep.RECEIVING_FILE_DATA
        )
        eof_pdu = EofPdu(
            file_size=file_size, file_checksum=crc32, pdu_conf=self.src_pdu_conf
        )
        self.dest_handler.pass_packet(eof_pdu)
        fsm_res = self.dest_handler.state_machine()
        self._state_checker(fsm_res, CfdpStates.IDLE, TransactionStep.IDLE)

    def _state_checker(
        self,
        fsm_res: Optional[FsmResult],
        expected_state: CfdpStates,
        expected_transaction: TransactionStep,
    ):
        if fsm_res is not None:
            self.assertEqual(fsm_res.states.state, expected_state)
            self.assertEqual(fsm_res.states.transaction, expected_transaction)
        self.assertEqual(self.dest_handler.states.state, expected_state)
        self.assertEqual(self.dest_handler.states.transaction, expected_transaction)

    def _source_simulator_transfer_init_with_metadata(
        self, checksum: ChecksumTypes, file_path: str, file_size: int
    ):
        """A file transfer on the receiving side is always initiated by sending a metadata PDU.
        This function simulates a CFDP source entity which initiates a file transfer by sending
        this PDU.
        """
        metadata_params = MetadataParams(
            checksum_type=checksum,
            closure_requested=self.closure_requested,
            source_file_name=file_path,
            dest_file_name=self.file_path.as_posix(),
            file_size=file_size,
        )
        file_transfer_init = MetadataPdu(
            params=metadata_params, pdu_conf=self.src_pdu_conf
        )
        self._state_checker(None, CfdpStates.IDLE, TransactionStep.IDLE)
        self.dest_handler.pass_packet(file_transfer_init)

    def tearDown(self) -> None:
        if self.file_path.exists():
            os.remove(self.file_path)
