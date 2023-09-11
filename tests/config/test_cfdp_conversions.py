from pathlib import Path
from unittest import TestCase

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import ProxyMessageType
from spacepackets.util import ByteFieldU8
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.config.cfdp import (
    cfdp_req_to_put_req_regular,
    cfdp_req_to_put_req_get_req,
    generic_cfdp_params_to_put_request,
    CfdpParams,
)


class TestCfdpParamsConversion(TestCase):
    def setUp(self) -> None:
        self.test_id_local = ByteFieldU8(1)
        self.test_dest_id_remote = ByteFieldU8(2)

    def _verify_regular_put_request(
        self, cfdp_params: CfdpParams, put_request: PutRequest
    ):
        self.assertEqual(put_request.source_file, Path(cfdp_params.source_file))
        self.assertEqual(put_request.dest_file, Path(cfdp_params.dest_file))

    def test_put_request_generation(self):
        cfdp_params = CfdpParams(source_file="hello.txt", dest_file="hello2.txt")
        put_request = cfdp_req_to_put_req_regular(cfdp_params, self.test_dest_id_remote)
        self._verify_regular_put_request(cfdp_params, put_request)

    def test_generic_put_request_generation(self):
        cfdp_params = CfdpParams(source_file="hello.txt", dest_file="hello2.txt")
        put_request = generic_cfdp_params_to_put_request(
            cfdp_params,
            local_id=self.test_id_local,
            remote_id=self.test_dest_id_remote,
            dest_id_proxy_put_req=self.test_id_local,
        )
        self._verify_regular_put_request(cfdp_params, put_request)

    def test_invalid_conversion_for_proxy_op(self):
        cfdp_param = CfdpParams(proxy_op=True)
        self.assertIsNone(
            cfdp_req_to_put_req_regular(cfdp_param, self.test_dest_id_remote)
        )

    def _verify_get_request(self, put_request: PutRequest, cfdp_params: CfdpParams):
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
            proxy_put_req_params.source_file_name,
            CfdpLv.from_str(cfdp_params.source_file),
        )
        self.assertEqual(
            proxy_put_req_params.dest_file_name, CfdpLv.from_str(cfdp_params.dest_file)
        )

    def test_get_request_put_request_generation(self):
        cfdp_params = CfdpParams(
            proxy_op=True, source_file="hello.txt", dest_file="hello2.txt"
        )
        put_request = cfdp_req_to_put_req_get_req(
            cfdp_params, self.test_id_local, self.test_dest_id_remote
        )
        self._verify_get_request(put_request, cfdp_params)

    def test_generic_conversion_function(self):
        cfdp_params = CfdpParams(
            proxy_op=True, source_file="hello.txt", dest_file="hello2.txt"
        )
        put_request = generic_cfdp_params_to_put_request(
            cfdp_params,
            self.test_id_local,
            self.test_dest_id_remote,
            self.test_id_local,
        )
        self._verify_get_request(put_request, cfdp_params)
