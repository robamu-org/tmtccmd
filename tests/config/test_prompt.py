from unittest import TestCase
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
            self.assertEqual(cmd_path, "acs")
            mocked_print.assert_called_once()
            printout = mocked_print.call_args[0][0]
            self.assertTrue("acs" in printout)
            self.assertTrue("ACS Subsystem" in printout)
            self.assertTrue("tcs" in printout)
            self.assertTrue("TCS Subsystem" in printout)

    def test_prompt_cmd_path_retry(self):
        self.base_tree()
        with patch(
            "tmtccmd.config.prompt.prompt_toolkit.prompt",
            side_effect=["acs/:r", "ping"],
        ) as prompt:
            cmd_path = prompt_cmd_path(self.cmd_tree)
            self.assertEqual(cmd_path, "ping")
            self.assertEqual(len(prompt.call_args_list), 2)
