from unittest import TestCase
import struct

from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import PusTelemetry

from tmtccmd.pus.s8_fsfw_action_defs import CustomSubservice
from tmtccmd.pus.tm.s8_fsfw_action import Service8FsfwDataReply


class TestSrv8FsfwTm(TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def test_unpack(self):
        example_obj_id = 0x01020304
        example_action_id = 0x04030201
        example_reply_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        tm = PusTelemetry(
            service=PusService.S8_FUNC_CMD,
            subservice=CustomSubservice.TM_DATA_REPLY,
            source_data=self.pack_data_reply_src_data(
                example_obj_id, example_action_id, example_reply_data
            ),
            timestamp=bytes(),
        )

        tm_packet = Service8FsfwDataReply(tm)
        self.assertEqual(tm_packet.object_id.value, example_obj_id)
        self.assertEqual(tm_packet.action_id, example_action_id)
        self.assertEqual(tm_packet.reply_data, example_reply_data)

    def test_unpack_invalid_subservice(self):
        example_obj_id = 0x01020304
        example_action_id = 0x04030201
        example_reply_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])

        for i in range(0, 255):
            if i == CustomSubservice.TM_DATA_REPLY:
                continue
            tm = PusTelemetry(
                service=PusService.S8_FUNC_CMD,
                subservice=CustomSubservice.TM_DATA_REPLY + 1,
                source_data=self.pack_data_reply_src_data(
                    example_obj_id, example_action_id, example_reply_data
                ),
                timestamp=bytes(),
            )
            with self.assertRaises(ValueError):
                Service8FsfwDataReply(tm)

    def pack_data_reply_src_data(self, obj_id: int, action_id: int, hk_data: bytes) -> bytes:
        return struct.pack("!I", obj_id) + struct.pack("!I", action_id) + hk_data
