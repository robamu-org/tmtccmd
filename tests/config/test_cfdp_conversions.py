from pathlib import Path
from unittest import TestCase

from spacepackets.util import ByteFieldU8
from tmtccmd.config.cfdp import (
    cfdp_req_to_put_req_regular,
    CfdpParams,
)


class TestCfdpParamsConversion(TestCase):
    def setUp(self) -> None:
        self.test_dest_id = ByteFieldU8(1)

    def test_put_request_generation(self):
        cfdp_param = CfdpParams(source_file="hello.txt", dest_file="hello2.txt")
        put_request = cfdp_req_to_put_req_regular(cfdp_param, self.test_dest_id)
        self.assertEqual(put_request.source_file, Path("hello.txt"))
        self.assertEqual(put_request.dest_file, "hello2.txt")
