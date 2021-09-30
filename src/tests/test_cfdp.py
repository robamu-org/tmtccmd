from unittest import TestCase
from tmtccmd.cfdp.tlv import CfdpTlv, TlvTypes
from tmtccmd.cfdp.lv import CfdpLv


class TestCfdp(TestCase):

    def test_tlvs(self):
        test_tlv = CfdpTlv(
            tlv_type=TlvTypes.FILESTORE_REQUEST,
            value=bytes([0, 1, 2, 3, 4])
        )
        self.assertEqual(test_tlv.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv.length, 5)
        self.assertEqual(test_tlv.value, bytes([0, 1, 2, 3, 4]))
        self.assertEqual(test_tlv.get_total_length(), 7)

        test_tlv_package = test_tlv.pack()
        test_tlv_unpacked = CfdpTlv.unpack(raw_bytes=test_tlv_package)
        self.assertEqual(test_tlv_unpacked.tlv_type, TlvTypes.FILESTORE_REQUEST)
        self.assertEqual(test_tlv_unpacked.length, 5)
        self.assertEqual(test_tlv_unpacked.value, bytes([0, 1, 2, 3, 4]))

        # Length field missmatch
        another_tlv = bytes([TlvTypes.ENTITY_ID, 1, 3, 4])
        another_tlv_unpacked = CfdpTlv.unpack(raw_bytes=another_tlv)
        self.assertEqual(another_tlv_unpacked.value, bytes([3]))
        self.assertEqual(another_tlv_unpacked.length, 1)

        faulty_tlv = bytes([TlvTypes.FILESTORE_REQUEST, 200, 2, 3])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Too much too pack
        faulty_values = bytes(300)
        self.assertRaises(ValueError, CfdpTlv, TlvTypes.FILESTORE_REQUEST, faulty_values)
        # Too short to unpack
        faulty_tlv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)
        # Invalid type when unpacking
        faulty_tlv = bytes([TlvTypes.ENTITY_ID + 3, 2, 1, 2])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_tlv)

    def test_lvs(self):
        test_values = bytes([0, 1, 2])
        test_lv = CfdpLv(
            value=test_values
        )
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.get_total_len(), 4)
        test_lv_packed = test_lv.pack()
        self.assertEqual(len(test_lv_packed), 4)
        self.assertEqual(test_lv_packed[0], 3)
        self.assertEqual(test_lv_packed[1: 1 + 3], test_values)

        CfdpLv.unpack(raw_bytes=test_lv_packed)
        self.assertEqual(test_lv.value, test_values)
        self.assertEqual(test_lv.len, 3)
        self.assertEqual(test_lv.get_total_len(), 4)

        # Too much too pack
        faulty_values = bytearray(300)
        self.assertRaises(ValueError, CfdpLv, faulty_values)
        # Too large to unpack
        faulty_values[0] = 20
        self.assertRaises(ValueError, CfdpLv.unpack, faulty_values[0:15])
        # Too short to unpack
        faulty_lv = bytes([0])
        self.assertRaises(ValueError, CfdpTlv.unpack, faulty_lv)
