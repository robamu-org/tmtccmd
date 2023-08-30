from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import ProxyMessageType
from spacepackets.util import ByteFieldU8
from tmtccmd.config.cfdp import (
    cfdp_req_to_put_req_regular,
    cfdp_req_to_put_req_proxy_get_req,
    CfdpParams,
)


class TestCfdpParamsConversion(TestCase):
    def setUp(self) -> None:
        self.test_id_local = ByteFieldU8(1)
        self.test_dest_id_remote = ByteFieldU8(2)

    def test_put_request_generation(self):
        cfdp_param = CfdpParams(source_file="hello.txt", dest_file="hello2.txt")
        put_request = cfdp_req_to_put_req_regular(cfdp_param, self.test_dest_id_remote)
        self.assertEqual(put_request.source_file, Path("hello.txt"))
        self.assertEqual(put_request.dest_file, "hello2.txt")

    def test_invalid_conversion_for_proxy_op(self):
        cfdp_param = CfdpParams(proxy_op=True)
        self.assertIsNone(
            cfdp_req_to_put_req_regular(cfdp_param, self.test_dest_id_remote)
        )

    def test_get_request_put_request_generation(self):
        cfdp_param = CfdpParams(
            proxy_op=True, source_file="hello.txt", dest_file="hello2.txt"
        )
        put_request = cfdp_req_to_put_req_proxy_get_req(
            cfdp_param, self.test_id_local, self.test_dest_id_remote
        )
        self.assertEqual(put_request.destination_id, self.test_dest_id_remote)
        self.assertIsNotNone(put_request.msgs_to_user)
        self.assertEqual(len(put_request.msgs_to_user), 1)
        msg_to_user = put_request.msgs_to_user[0]
        self.assertTrue(msg_to_user.is_reserved_cfdp_message())
        reserved_msg = msg_to_user.to_reserved_msg_tlv()
        self.assertTrue(reserved_msg.is_cfdp_proxy_operation())
        self.assertEqual(
            reserved_msg.get_cfdp_proxy_message_type(), ProxyMessageType.PUT_REQUEST
        )
        proxy_put_req_params = reserved_msg.get_proxy_put_request_params()
        self.assertIsNotNone(proxy_put_req_params)
        self.assertEqual(proxy_put_req_params.dest_entity_id, self.test_id_local)
        self.assertEqual(
            proxy_put_req_params.source_file_name, CfdpLv.from_str("hello.txt")
        )
        self.assertEqual(
            proxy_put_req_params.dest_file_name, CfdpLv.from_str("hello2.txt")
        )
