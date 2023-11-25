from unittest import TestCase

from prompt_toolkit.history import InMemoryHistory
from tmtccmd.config.prompt import prompt_cmd_path
from tmtccmd.config.tmtc import CmdTreeNode
from unittest.mock import MagicMock, patch


class TestPromptFunc(TestCase):
    def setUp(self) -> None:
        self.cmd_tree = CmdTreeNode.root_node()
        return super().setUp()

    def base_tree(self):
        self.cmd_tree.add_child(CmdTreeNode("acs", "ACS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("tcs", "TCS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

    @patch("builtins.print")
    def test_prompt_cmd_path_simple_print(self, _: MagicMock):
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt", side_effect=[":p", "/"]
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree)
            prompt.assert_not_called()
            self.assertEqual(cmd_path, "/")

    @patch("builtins.print")
    def test_prompt_cmd_path_full_print(self, mocked_print: MagicMock):
        self.base_tree()
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt", side_effect=[":pf", "acs"]
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree)
            self.assertEqual(len(prompt.call_args_list), 2)
            self.assertEqual(cmd_path, "/acs")
            call_list = mocked_print.call_args_list
            self.assertEqual(len(call_list), 2)
            help_txt = mocked_print.call_args_list[0].args[0]
            self.assertTrue("Additional commands for prompt:" in help_txt)
            self.assertTrue(":p[b][f][<depth>] Tree Print" in help_txt)
            self.assertTrue(":r Retry" in help_txt)
            self.assertTrue(":h Help Text" in help_txt)
            printout = mocked_print.call_args_list[1].args[0]
            self.assertTrue("acs" in printout)
            self.assertTrue("ACS Subsystem" in printout)
            self.assertTrue("tcs" in printout)
            self.assertTrue("TCS Subsystem" in printout)

    def test_prompt_cmd_path_retry_explicit(self):
        self.base_tree()
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt",
            side_effect=["acs/:r", "ping"],
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree)
            self.assertEqual(cmd_path, "/ping")
            self.assertEqual(len(prompt.call_args_list), 2)

    def test_prompt_cmd_path_retry_prompted(self):
        self.base_tree()
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt",
            side_effect=["acss", "acs"],
        ) as prompt_mock:
            with patch(
                "tmtccmd.config.prompt.input",
                return_value="yes",
            ) as input_mock:
                cmd_path = prompt_cmd_path(self.cmd_tree)
                self.assertEqual(cmd_path, "/acs")
                self.assertEqual(len(prompt_mock.call_args_list), 2)
                self.assertEqual(len(input_mock.call_args_list), 1)

    @patch("builtins.print")
    def test_prompt_help_reprint(self, mocked_print: MagicMock):
        self.base_tree()
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt", side_effect=[":h", "acs"]
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree)
            self.assertEqual(len(prompt.call_args_list), 2)
            self.assertEqual(cmd_path, "/acs")
            call_list = mocked_print.call_args_list
            self.assertEqual(len(call_list), 2)
            help_txt = mocked_print.call_args_list[0].args[0]
            self.assertTrue("Additional commands for prompt:" in help_txt)
            self.assertTrue(":p[b][f][<depth>] Tree Print" in help_txt)
            self.assertTrue(":r Retry" in help_txt)
            self.assertTrue(":h Help Text" in help_txt)
            help_txt_2 = mocked_print.call_args_list[1].args[0]
            self.assertEqual(help_txt, help_txt_2)

    def test_cmd_history(self):
        self.base_tree()
        history = InMemoryHistory()
        history.append_string("test")
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt", side_effect=["ping"]
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree, history=history)
            self.assertEqual(len(prompt.call_args_list), 1)
            self.assertEqual(cmd_path, "/ping")
