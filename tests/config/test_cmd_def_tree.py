from unittest import TestCase
from tmtccmd.config.tmtc import CmdTreeNode


class TestCmdDefTree(TestCase):
    def setUp(self) -> None:
        self.cmd_tree = CmdTreeNode.root_node()

    def base_tree(self):
        self.cmd_tree.add_child(CmdTreeNode("acs", "ACS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("tcs", "TCS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

    def test_state(self):
        self.base_tree()
        self.assertEqual(self.cmd_tree.name, "/")
        self.assertEqual(self.cmd_tree.children["acs"].name, "acs")
        self.assertEqual(self.cmd_tree.children["acs"].description, "ACS Subsystem")
        self.assertEqual(self.cmd_tree.children["acs"].children, {})
        assert self.cmd_tree.children["acs"].parent is not None
        self.assertEqual(self.cmd_tree.children["acs"].parent.name, "/")

        self.assertEqual(self.cmd_tree.children["tcs"].name, "tcs")
        self.assertEqual(self.cmd_tree.children["tcs"].description, "TCS Subsystem")
        self.assertEqual(self.cmd_tree.children["tcs"].children, {})
        assert self.cmd_tree.children["tcs"].parent is not None
        self.assertEqual(self.cmd_tree.children["tcs"].parent.name, "/")

        self.assertEqual(self.cmd_tree.children["ping"].name, "ping")
        self.assertEqual(self.cmd_tree.children["ping"].description, "Ping Command")
        self.assertEqual(self.cmd_tree.children["ping"].children, {})
        assert self.cmd_tree.children["ping"].parent is not None
        self.assertEqual(self.cmd_tree.children["ping"].parent.name, "/")

        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.assertEqual(len(self.cmd_tree.children["acs"].children), 1)
        acs_ctrl_child = self.cmd_tree.children["acs"].children["acs_ctrl"]
        self.assertEqual(acs_ctrl_child.name, "acs_ctrl")
        self.assertEqual(acs_ctrl_child.description, "ACS Controller")
        assert acs_ctrl_child.parent is not None
        self.assertEqual(acs_ctrl_child.parent.name, "acs")

    def test_named_dict(self):
        self.base_tree()
        name_dict = self.cmd_tree.name_dict
        root_dict = name_dict.get("/")
        assert root_dict is not None
        assert "acs" in root_dict
        assert root_dict.get("acs") is None
