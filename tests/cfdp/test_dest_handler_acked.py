from spacepackets.cfdp import TransmissionMode
from .test_dest_handler import TestDestHandlerBase


class TestDestHandlerAcked(TestDestHandlerBase):
    def setUp(self) -> None:
        self.common_setup(TransmissionMode.ACKNOWLEDGED)

    def test_basic(self):
        # Basic acknowledged empty file transfer.
        pass
