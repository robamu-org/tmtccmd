import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from tmtccmd.com.ser_utils import load_baud_rate_from_json, load_baud_rate_from_toml
from tmtccmd.com.utils import determine_com_if
from tmtccmd.util.json import JsonKeyNames


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

    def test_load_serial_baud_from_json(self):
        pass

    def tearDown(self) -> None:
        path = Path(self.json_file)
        if path.exists():
            os.remove(path)


class TestLoadBaudRateFromJson(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cfg_path = Path(self.tmp_dir.name) / "config.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_valid_key_returns_int(self):
        self.cfg_path.write_text(json.dumps({JsonKeyNames.SERIAL_BAUDRATE.value: 115200}))
        self.assertEqual(load_baud_rate_from_json(str(self.cfg_path)), 115200)

    def test_missing_key_returns_none(self):
        self.cfg_path.write_text(json.dumps({"other_key": 123}))
        self.assertIsNone(load_baud_rate_from_json(str(self.cfg_path)))


class TestLoadBaudRateFromToml(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cfg_path = Path(self.tmp_dir.name) / "config.toml"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_valid_key_returns_int(self):
        self.cfg_path.write_text("[serial]\nbaud = 115200\n")
        self.assertEqual(load_baud_rate_from_toml(str(self.cfg_path)), 115200)

    def test_missing_key_returns_none(self):
        self.cfg_path.write_text("[serial]\nblahblub= 115200\n")
        self.assertIsNone(load_baud_rate_from_toml(str(self.cfg_path)))
