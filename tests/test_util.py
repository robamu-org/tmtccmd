from unittest import TestCase

from tmtccmd.util.obj_id import (
    ComponentIdU8,
    ComponentIdU16,
    ComponentIdU32,
)


class TestObjectId(TestCase):
    def test_basic(self):
        obj_id0 = ComponentIdU32(1, "Some Name")
        self.assertEqual(str(obj_id0), "Object ID Some Name with ID 0x00000001")
        self.assertEqual(obj_id0.__repr__(), "ComponentIdU32(object_id=1, name='Some Name')")
        self.assertEqual(obj_id0.as_bytes, bytes([0x00, 0x00, 0x00, 0x01]))
        self.assertEqual(obj_id0.as_hex_string, "0x00000001")
        self.assertEqual(int(obj_id0), 1)
        obj_id1 = ComponentIdU32(1, "Other Name")
        self.assertEqual(obj_id0, obj_id1)
        obj_from_raw = ComponentIdU32.from_bytes(obj_id0.as_bytes)
        self.assertEqual(obj_from_raw, obj_id0)
        with self.assertRaises(ValueError):
            ComponentIdU32.from_bytes(b"")
        with self.assertRaises(ValueError):
            ComponentIdU32.from_bytes(bytes([0, 1, 2]))
        with self.assertRaises(ValueError):
            obj_id1.obj_id = -1

    def test_diff_types(self):
        obj_id_u8 = ComponentIdU8(1, "U8 ID 0")
        self.assertEqual(obj_id_u8.as_bytes, bytes([1]))
        self.assertEqual(obj_id_u8.as_hex_string, "0x01")
        self.assertEqual(obj_id_u8.byte_len, 1)
        obj_id_u16 = ComponentIdU16(2, "U16 ID 2")
        self.assertEqual(obj_id_u16.as_bytes, bytes([0, 2]))
        self.assertEqual(obj_id_u16.as_hex_string, "0x0002")
        self.assertEqual(obj_id_u16.byte_len, 2)
        obj_id_u32 = ComponentIdU32(1, "U32 ID 1")
        test_dict = dict()
        test_dict.update({obj_id_u8: obj_id_u8.name})
        test_dict.update({obj_id_u16: obj_id_u16.name})
        test_dict.update({obj_id_u32: obj_id_u32.name})
        self.assertEqual(len(test_dict), 3)
        obj_id_u8_from_raw = ComponentIdU8.from_bytes(obj_id_u8.as_bytes)
        self.assertEqual(obj_id_u8_from_raw, obj_id_u8)
        obj_id_u16_from_raw = ComponentIdU16.from_bytes(obj_id_u16.as_bytes)
        self.assertEqual(obj_id_u16_from_raw, obj_id_u16)
        obj_id_u32_from_raw = ComponentIdU32.from_bytes(obj_id_u32.as_bytes)
        self.assertEqual(obj_id_u32_from_raw, obj_id_u32)
