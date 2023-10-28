from spacepackets.cfdp import NULL_CHECKSUM_U32, TransmissionMode
from .test_dest_handler import TestDestHandlerBase


class TestDestHandlerAcked(TestDestHandlerBase):
    def setUp(self) -> None:
        self.common_setup(TransmissionMode.ACKNOWLEDGED)

    def test_basic(self):
        # Basic acknowledged empty file transfer.
        self._generic_transfer_init(0)
        fsm_res = self._generic_insert_eof_pdu(0, NULL_CHECKSUM_U32)
        self._generic_eof_recv_indication_check(fsm_res)
        # Now an ACK packet has to be generated for the EOF packet.
        pass
