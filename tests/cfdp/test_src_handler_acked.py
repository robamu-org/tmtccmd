from spacepackets.cfdp import TransmissionMode
from .test_src_handler import TestCfdpSourceHandler


class TestSourceHandlerAcked(TestCfdpSourceHandler):
    def setUp(self) -> None:
        self.common_setup(True, TransmissionMode.ACKNOWLEDGED)

    def test_empty_file_transfer(self):
        pass
