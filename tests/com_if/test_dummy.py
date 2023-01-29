from unittest import TestCase

from spacepackets.ecss import PusTelecommand
from tmtccmd.com.dummy import DummyComIF


class TestDummy(TestCase):
    def test_dummy_if(self):
        dummy_com_if = DummyComIF()
        self.assertFalse(dummy_com_if.is_open())
        dummy_com_if.open()
        self.assertTrue(dummy_com_if.is_open())
        self.assertFalse(dummy_com_if.initialized)
        dummy_com_if.initialize()
        self.assertTrue(dummy_com_if.initialized)
        self.assertFalse(dummy_com_if.data_available())
        dummy_com_if.send(PusTelecommand(service=17, subservice=1).pack())
        self.assertTrue(dummy_com_if.data_available())
        replies = dummy_com_if.receive()
        # Full verification set (acceptance, start and completion) and ping reply
        self.assertEqual(len(replies), 4)
