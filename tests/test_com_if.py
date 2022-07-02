import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from spacepackets.ecss import PusTelecommand
from tmtccmd.com_if.dummy import DummyComIF
from tmtccmd.com_if.utils import determine_com_if


class TestComIF(TestCase):
    def setUp(self) -> None:
        self.json_file = "test.json"

    def test_com_if_utils(self):
        with patch("tmtccmd.com_if.utils.wrapped_prompt", side_effect=["0", "yes"]):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
            with open(self.json_file) as file:
                lines = file.readlines()
                lines[0] = "{\n"
                lines[1] = '    "com_if": "test-com-if"\n'
                lines[2] = "}"
            os.remove(self.json_file)
        with patch("tmtccmd.com_if.utils.wrapped_prompt", side_effect=["0", "no"]):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
            with open(self.json_file) as file:
                lines = file.readlines()
                lines[0] = "{}"
        with patch(
            "tmtccmd.com_if.utils.wrapped_prompt",
            side_effect=["1", "0", "no"],
        ):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
        with patch(
            "tmtccmd.com_if.utils.wrapped_prompt",
            side_effect=["blub", "0", "no"],
        ):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")

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

    def tearDown(self) -> None:
        path = Path(self.json_file)
        if path.exists():
            os.remove(path)
