import struct
from unittest import TestCase

from spacepackets.ecss import Ptc, PfcUnsigned, PfcSigned, PfcReal
from tmtccmd.pus.s20_fsfw_param_defs import (
    create_scalar_boolean_parameter,
    parse_scalar_param,
    create_scalar_double_parameter,
    create_scalar_float_parameter,
    create_scalar_i8_parameter,
    create_scalar_i16_parameter,
    create_scalar_i32_parameter,
    create_scalar_u16_parameter,
    create_scalar_u32_parameter,
    create_scalar_u8_parameter,
    create_vector_float_parameter,
    create_vector_double_parameter,
    create_matrix_float_parameter,
    create_matrix_double_parameter,
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

    def test_u8_param(self):
        u8_param = create_scalar_u8_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=255
        )
        self.assertEqual(u8_param.param_raw[0], 255)
        self.assertEqual(u8_param.ptc, Ptc.UNSIGNED)
        self.assertEqual(u8_param.pfc, PfcSigned.ONE_BYTE)
        self.assertEqual(u8_param.rows, 1)
        self.assertEqual(u8_param.columns, 1)
        param = parse_scalar_param(u8_param)
        self.assertEqual(param, 255)

    def test_u16_param(self):
        u16_param = create_scalar_u16_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=60000
        )
        self.assertEqual(u16_param.ptc, Ptc.UNSIGNED)
        self.assertEqual(u16_param.pfc, PfcUnsigned.TWO_BYTES)
        self.assertEqual(u16_param.rows, 1)
        self.assertEqual(u16_param.columns, 1)
        param = parse_scalar_param(u16_param)
        self.assertEqual(param, 60000)

    def test_u32_param(self):
        u32_param = create_scalar_u32_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=79932932
        )
        self.assertEqual(u32_param.ptc, Ptc.UNSIGNED)
        self.assertEqual(u32_param.pfc, PfcUnsigned.FOUR_BYTES)
        self.assertEqual(u32_param.rows, 1)
        self.assertEqual(u32_param.columns, 1)
        param = parse_scalar_param(u32_param)
        self.assertEqual(param, 79932932)

    def test_i8_param(self):
        i8_param = create_scalar_i8_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=-22
        )
        self.assertEqual(struct.unpack("!b", i8_param.param_raw)[0], -22)
        self.assertEqual(i8_param.ptc, Ptc.SIGNED)
        self.assertEqual(i8_param.pfc, PfcSigned.ONE_BYTE)
        self.assertEqual(i8_param.rows, 1)
        self.assertEqual(i8_param.columns, 1)
        param = parse_scalar_param(i8_param)
        self.assertEqual(param, -22)

    def test_i16_param(self):
        i16_param = create_scalar_i16_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=-30000
        )
        self.assertEqual(struct.unpack("!h", i16_param.param_raw)[0], -30000)
        self.assertEqual(i16_param.ptc, Ptc.SIGNED)
        self.assertEqual(i16_param.pfc, PfcSigned.TWO_BYTES)
        self.assertEqual(i16_param.rows, 1)
        self.assertEqual(i16_param.columns, 1)
        param = parse_scalar_param(i16_param)
        self.assertEqual(param, -30000)

    def test_i32_param(self):
        i32_param = create_scalar_i32_parameter(
            self.obj_id, domain_id=25, unique_id=30, parameter=-70000
        )
        self.assertEqual(struct.unpack("!i", i32_param.param_raw)[0], -70000)
        self.assertEqual(i32_param.ptc, Ptc.SIGNED)
        self.assertEqual(i32_param.pfc, PfcSigned.FOUR_BYTES)
        self.assertEqual(i32_param.rows, 1)
        self.assertEqual(i32_param.columns, 1)
        param = parse_scalar_param(i32_param)
        self.assertEqual(param, -70000)

    def test_double_vec(self):
        double_vec = [3.0, -52.4, 38.32]
        double_vec_param = create_vector_double_parameter(
            self.obj_id, domain_id=30, unique_id=93, parameters=double_vec
        )
        self.assertEqual(double_vec_param.rows, 1)
        self.assertEqual(double_vec_param.columns, 3)
        self.assertEqual(double_vec_param.ptc, Ptc.REAL)
        self.assertEqual(double_vec_param.pfc, PfcReal.DOUBLE_PRECISION_IEEE)
        self.assertEqual(len(double_vec_param.param_raw), 24)
        self.assertTrue(
            abs(struct.unpack("!d", double_vec_param.param_raw[0:8])[0] - 3.0) < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", double_vec_param.param_raw[8:16])[0]) - 52.4
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", double_vec_param.param_raw[16:24])[0] - 38.32)
            < 0.0001
        )

    def test_float_vec(self):
        float_vec = [3.0, -52.4, 38.32]
        double_vec_param = create_vector_float_parameter(
            self.obj_id, domain_id=30, unique_id=80, parameters=float_vec
        )
        self.assertEqual(double_vec_param.rows, 1)
        self.assertEqual(double_vec_param.columns, 3)
        self.assertEqual(double_vec_param.ptc, Ptc.REAL)
        self.assertEqual(double_vec_param.pfc, PfcReal.FLOAT_SIMPLE_PRECISION_IEEE)
        self.assertEqual(len(double_vec_param.param_raw), 12)
        self.assertTrue(
            abs(struct.unpack("!f", double_vec_param.param_raw[0:4])[0] - 3.0) < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!f", double_vec_param.param_raw[4:8])[0]) - 52.4 < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!f", double_vec_param.param_raw[8:12])[0]) - 38.32
            < 0.0001
        )

    def test_float_matrix(self):
        float_matrix = [
            [3.0, -52.4, 28.32],
            [94924.42, -30232.32, 9393.2],
        ]
        float_matrix_param = create_matrix_float_parameter(
            self.obj_id, domain_id=30, unique_id=80, parameters=float_matrix
        )
        self.assertEqual(float_matrix_param.rows, 2)
        self.assertEqual(float_matrix_param.columns, 3)
        self.assertEqual(float_matrix_param.ptc, Ptc.REAL)
        self.assertEqual(float_matrix_param.pfc, PfcReal.FLOAT_SIMPLE_PRECISION_IEEE)
        self.assertEqual(len(float_matrix_param.param_raw), 24)
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[0:4])[0] - 3.0)
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[4:8])[0]) - 52.4
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[8:12])[0]) - 28.32
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[12:16])[0]) - 94924.42
            < 0.01
        )
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[16:20])[0]) - 30232.32
            < 0.01
        )
        self.assertTrue(
            abs(struct.unpack("!f", float_matrix_param.param_raw[20:24])[0]) - 9393.2
            < 0.001
        )

    def test_double_matrix(self):
        double_matrix = [
            [3.0, -52.4, 28.32],
            [94924.42, -30232.32, 9393.2],
        ]
        float_matrix_param = create_matrix_double_parameter(
            self.obj_id, domain_id=30, unique_id=80, parameters=double_matrix
        )
        self.assertEqual(float_matrix_param.rows, 2)
        self.assertEqual(float_matrix_param.columns, 3)
        self.assertEqual(float_matrix_param.ptc, Ptc.REAL)
        self.assertEqual(float_matrix_param.pfc, PfcReal.DOUBLE_PRECISION_IEEE)
        self.assertEqual(len(float_matrix_param.param_raw), 48)
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[0:8])[0] - 3.0)
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[8:16])[0]) - 52.4
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[16:24])[0]) - 28.32
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[24:32])[0]) - 94924.42
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[32:40])[0]) - 30232.32
            < 0.0001
        )
        self.assertTrue(
            abs(struct.unpack("!d", float_matrix_param.param_raw[40:48])[0]) - 9393.2
            < 0.00001
        )
