import struct
from unittest import TestCase

from spacepackets.ecss import Ptc, PfcUnsigned
from tmtccmd.pus.s20_fsfw_param_defs import (
    create_scalar_boolean_parameter,
    parse_scalar_param,
    create_scalar_double_parameter,
    create_scalar_float_parameter,
)


class TestSrv20(TestCase):
    def setUp(self) -> None:
        self.obj_id = bytes([0x01, 0x02, 0x03, 0x04])
        self.boolean_param = create_scalar_boolean_parameter(
            object_id=self.obj_id, domain_id=1, unique_id=5, parameter=True
        )

    def test_param_id(self):
        expected_u32 = (1 << 24) | (5 << 16)
        param_id_u32 = self.boolean_param.param_id.as_u32()
        self.assertEqual(expected_u32, param_id_u32)

    def test_basic_boolean_param(self):
        self.assertEqual(self.boolean_param.ptc, Ptc.UNSIGNED)
        self.assertEqual(self.boolean_param.pfc, PfcUnsigned.ONE_BYTE)
        app_data_raw = self.boolean_param.pack()
        self.assertEqual(self.obj_id, app_data_raw[0:4])
        self.assertEqual(app_data_raw[4], 1)
        self.assertEqual(app_data_raw[5], 5)
        self.assertEqual(struct.unpack("!H", app_data_raw[6:8])[0], 0)
        self.assertEqual(app_data_raw[8], Ptc.UNSIGNED)
        self.assertEqual(app_data_raw[9], PfcUnsigned.ONE_BYTE)
        self.assertEqual(app_data_raw[10], 1)
        self.assertEqual(app_data_raw[11], 1)

    def test_float_param(self):
        double_param = create_scalar_float_parameter(
            self.obj_id, domain_id=12, unique_id=25, parameter=-12.0
        )
        raw = double_param.pack()
        self.assertEqual(len(raw), 16)

    def test_double_param(self):
        double_param = create_scalar_double_parameter(
            self.obj_id, domain_id=12, unique_id=25, parameter=3923929.0
        )
        raw = double_param.pack()
        self.assertEqual(len(raw), 20)
        double_val = struct.unpack("!d", raw[12:20])[0]
        self.assertTrue(abs(double_val - 3923929.0) < 0.00001)

    def test_param_extraction_bool(self):
        param = parse_scalar_param(self.boolean_param)
        self.assertEqual(param, 1)
        self.assertEqual(self.boolean_param.parse_scalar_param(), 1)

    def test_param_extraction_float(self):
        double_param = create_scalar_float_parameter(
            self.obj_id, domain_id=12, unique_id=25, parameter=-12.0
        )
        param = parse_scalar_param(double_param)
        self.assertTrue(abs(param + 12.0) < 0.00001)
        self.assertTrue(abs(double_param.parse_scalar_param() + 12.0) < 0.00001)

    def test_param_extraction_double(self):
        double_param = create_scalar_double_parameter(
            self.obj_id, domain_id=12, unique_id=25, parameter=3932.32
        )
        param = parse_scalar_param(double_param)
        self.assertTrue(abs(param - 3932.32) < 0.00001)
        self.assertTrue(abs(double_param.parse_scalar_param() - 3932.32) < 0.00001)
