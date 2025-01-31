from unittest import TestCase
import struct

from spacepackets.ecss.defs import PusService
from spacepackets.ecss.tm import PusTelemetry

from tmtccmd.pus.s3_fsfw_hk import Subservice
from tmtccmd.pus.tm.s3_fsfw_hk import Service3FsfwHkPacket


class TestSrv3FsfwTm(TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def test_unpack(self):
        example_obj_id = 0x01020304
        example_set_id = 0x04030201
        example_hk_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        tm = PusTelemetry(
            service=PusService.S8_FUNC_CMD,
            subservice=Subservice.TM_HK_REPORT,
            source_data=self.pack_data_reply_src_data(
                example_obj_id, example_set_id, example_hk_data
            ),
            timestamp=bytes(),
        )

        tm_packet = Service3FsfwHkPacket(tm)
        self.assertEqual(tm_packet.object_id.value, example_obj_id)
        self.assertEqual(tm_packet.set_id, example_set_id)
        self.assertEqual(tm_packet.hk_data, example_hk_data)

    def test_unpack_invalid_subservice(self):
        example_obj_id = 0x01020304
        example_action_id = 0x04030201
        example_reply_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        for i in range(0, 255):
            if i == Subservice.TM_HK_REPORT or i == Subservice.TM_DIAGNOSTICS_REPORT:
                continue
            tm = PusTelemetry(
                service=PusService.S8_FUNC_CMD,
                subservice=Subservice.TM_REPORT_DIAG_REPORT_STRUCTURES,
                source_data=self.pack_data_reply_src_data(
                    example_obj_id, example_action_id, example_reply_data
                ),
                timestamp=bytes(),
            )
            with self.assertRaises(ValueError):
                Service3FsfwHkPacket(tm)

    def pack_data_reply_src_data(self, obj_id: int, action_id: int, hk_data: bytes) -> bytes:
        return struct.pack("!I", obj_id) + struct.pack("!I", action_id) + hk_data
