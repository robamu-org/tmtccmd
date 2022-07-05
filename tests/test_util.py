from unittest import TestCase

from tmtccmd.utility import ObjectIdU32


class TestObjectId(TestCase):
    def test_basic(self):
        obj_id0 = ObjectIdU32(1, "Some Name")
        self.assertEqual(str(obj_id0), "32-bit Object ID Some Name with ID 0x00000001")
        self.assertEqual(
            obj_id0.__repr__(), "ObjectIdU32(object_id=1, name='Some Name')"
        )
        self.assertEqual(obj_id0.as_bytes, bytes([0x00, 0x00, 0x00, 0x01]))
        self.assertEqual(obj_id0.as_hex_string, "0x00000001")
        self.assertEqual(obj_id0.as_int, 1)
        obj_id1 = ObjectIdU32(1, "Other Name")
        self.assertEqual(obj_id0, obj_id1)
        obj_from_raw = ObjectIdU32.from_bytes(obj_id0.as_bytes)
        self.assertEqual(obj_from_raw, obj_id0)
        with self.assertRaises(ValueError):
            ObjectIdU32.from_bytes(bytes())
        with self.assertRaises(ValueError):
            ObjectIdU32.from_bytes(bytes([0, 1, 2]))
        with self.assertRaises(ValueError):
            ObjectIdU32.from_bytes(bytes([0, 1, 2, 3, 4]))
