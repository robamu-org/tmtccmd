from unittest import TestCase

from spacepackets.ecss import PfcUnsigned, Ptc, PusTc, PusService
from tmtccmd.pus.s20_fsfw_param_defs import Parameter, CustomSubservice
from tmtccmd.pus.s20_fsfw_param import (
    create_load_param_cmd,
    create_scalar_boolean_parameter,
)


class TestSrv20FsfwTc(TestCase):
    def setUp(self):
        self.obj_id = bytes([0x01, 0x02, 0x03, 0x04])
        self.boolean_param = create_scalar_boolean_parameter(
            object_id=self.obj_id, domain_id=1, unique_id=5, parameter=True
        )
        self.assertEqual(self.boolean_param.ptc, Ptc.UNSIGNED)
        self.assertEqual(self.boolean_param.pfc, PfcUnsigned.ONE_BYTE)
        self.tc = create_load_param_cmd(self.boolean_param, 0x05)

    def test_basic(self):
        # 12 bytes of generic parameter header + 1 byte parameter itself
        self.assertEqual(len(self.tc.app_data), 13)
        self.assertEqual(self.tc.apid, 0x05)
        self.assertEqual(self.tc.service, PusService.S20_PARAMETER)
        self.assertEqual(self.tc.subservice, CustomSubservice.TC_LOAD)

    def test_unpack(self):
        raw_tc = self.tc.pack()
        unpacked = PusTc.unpack(raw_tc)
        boolean_param_conv_back = Parameter.unpack(unpacked.app_data)
        self.assertEqual(boolean_param_conv_back, self.boolean_param)
