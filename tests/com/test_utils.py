import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from tmtccmd.com.utils import determine_com_if


class TestUtils(TestCase):
    def setUp(self) -> None:
        self.json_file = "test.json"

    def test_com_if_utils(self):
        with patch("tmtccmd.com.utils.wrapped_prompt", side_effect=["0", "yes"]):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
            with open(self.json_file) as file:
                lines = file.readlines()
                lines[0] = "{\n"
                lines[1] = '    "com_if": "test-com-if"\n'
                lines[2] = "}"
            os.remove(self.json_file)
        with patch("tmtccmd.com.utils.wrapped_prompt", side_effect=["0", "no"]):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
            with open(self.json_file) as file:
                lines = file.readlines()
                lines[0] = "{}"
        with patch(
            "tmtccmd.com.utils.wrapped_prompt",
            side_effect=["1", "0", "no"],
        ):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")
        with patch(
            "tmtccmd.com.utils.wrapped_prompt",
            side_effect=["blub", "0", "no"],
        ):
            test_dict = {"test-com-if": ("Some more info", None)}
            com_if = determine_com_if(test_dict, self.json_file, True)
            self.assertEqual(com_if, "test-com-if")

    def tearDown(self) -> None:
        path = Path(self.json_file)
        if path.exists():
            os.remove(path)
