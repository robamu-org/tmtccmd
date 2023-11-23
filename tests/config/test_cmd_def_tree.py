import os
from typing import Optional
from unittest import TestCase
from tmtccmd.config.tmtc import CmdTreeNode


class TestCmdDefTree(TestCase):
    def setUp(self) -> None:
        self.cmd_tree = CmdTreeNode.root_node()

    def base_tree(self):
        self.cmd_tree.add_child(CmdTreeNode("acs", "ACS Subsystem"))
        self.cmd_tree.add_child(CmdTreeNode("tcs", "TCS Subsystem"))

    def tree_with_two_layers(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )

    def test_state(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
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

    def test_path_contained(self):
        self.base_tree()
        self.assertTrue(self.cmd_tree.contains_path("/"))

    def test_path_contained_invalid_input(self):
        self.assertFalse(self.cmd_tree.contains_path(""))

    def test_extract_node_invalid_input(self):
        self.assertIsNone(self.cmd_tree.extract_subnode(""))

    def test_extract_node_not_contained(self):
        self.tree_with_two_layers()
        self.assertIsNone(self.cmd_tree.extract_subnode("aocs"))

    def test_extract_subnode_simple(self):
        self.tree_with_two_layers()
        acs_node = self.cmd_tree.extract_subnode("acs")
        assert acs_node is not None
        self.assertEqual(acs_node.name, "acs")
        self.assertIsNotNone(acs_node.children["acs_ctrl"] is not None)

    def _generic_subnode_relativ_path_test(self, acs_ctrl_node: Optional[CmdTreeNode]):
        assert acs_ctrl_node is not None
        self.assertEqual(acs_ctrl_node.name, "acs_ctrl")
        self.assertIsNotNone(acs_ctrl_node.children["update_params"] is not None)

    def test_extract_subnode_relative_path(self):
        self.tree_with_two_layers()
        self.cmd_tree["acs"]["acs_ctrl"].add_child(
            CmdTreeNode("update_params", "Update Parameters")
        )
        self._generic_subnode_relativ_path_test(
            self.cmd_tree.extract_subnode("acs/acs_ctrl")
        )

    def test_extract_subnode_relativ_path_by_list(self):
        self.tree_with_two_layers()
        self.cmd_tree["acs"]["acs_ctrl"].add_child(
            CmdTreeNode("update_params", "Update Parameters")
        )
        self._generic_subnode_relativ_path_test(
            self.cmd_tree.extract_subnode_by_node_list(["acs", "acs_ctrl"])
        )

    def test_path_contained_acs(self):
        self.base_tree()
        self.assertTrue(self.cmd_tree.contains_path("/acs"))

    def test_path_contained_tcs(self):
        self.base_tree()
        self.assertTrue(self.cmd_tree.contains_path("/tcs"))

    def test_path_contained_acs_ctrl(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.assertTrue(self.cmd_tree.contains_path("/acs/acs_ctrl"))

    def test_named_dict(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        name_dict = self.cmd_tree.name_dict
        root_dict = name_dict.get("/")
        assert root_dict is not None
        assert "tcs" in root_dict
        assert root_dict.get("tcs") is None
        assert "acs" in root_dict
        acs_dict = root_dict.get("acs")
        assert acs_dict is not None
        assert "acs_ctrl" in acs_dict
        assert acs_dict.get("acs_ctrl") is None

    def test_printout_empty(self):
        self.assertEqual(str(self.cmd_tree), f"/{os.linesep}")

    def test_prinout_one_sublevel(self):
        self.base_tree()
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        print(str(self.cmd_tree))
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_prinout_two_sublevels(self):
        self.tree_with_two_layers()
        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── acs_ctrl{os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_two_sublevels_one_cutoff(self):
        self.tree_with_two_layers()
        printout = self.cmd_tree.str_for_tree(False, 1)
        print(printout)
        self.assertEqual(
            printout,
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── ... (cut-off, maximum depth 1){os.linesep}"
                f"├── tcs{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_3(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.cmd_tree.children["tcs"].add_child(
            CmdTreeNode("tcs_ctrl", "TCS Controller")
        )

        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  └── acs_ctrl{os.linesep}"
                f"└── tcs{os.linesep}"
                f"   └── tcs_ctrl{os.linesep}"
            ),
        )

    def test_printout_4(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.cmd_tree.children["acs"].add_child(CmdTreeNode("mgm_0", "MGM 0"))
        self.cmd_tree.children["acs"].children["mgm_0"].add_child(
            CmdTreeNode("update_cfg", "Update Configuration")
        )
        self.cmd_tree.children["tcs"].add_child(
            CmdTreeNode("tcs_ctrl", "TCS Controller")
        )
        self.cmd_tree.children["tcs"].add_child(CmdTreeNode("pt1000_0", "PT1000 0"))
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── update_cfg{os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  └── pt1000_0{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_5(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        self.cmd_tree.children["acs"].add_child(CmdTreeNode("mgm_0", "MGM 0"))
        self.cmd_tree.children["acs"].children["mgm_0"].add_child(
            CmdTreeNode("update_cfg", "Update Configuration")
        )
        tcs_ctrl = CmdTreeNode("tcs_ctrl", "TCS Controller")
        tcs_ctrl.add_child(CmdTreeNode("set_param", "Set Parameter"))
        self.cmd_tree.children["tcs"].add_child(tcs_ctrl)
        pt1000_node = CmdTreeNode("pt1000_0", "PT1000 0")
        pt1000_node.add_child(CmdTreeNode("set_mode", "Set Mode"))
        self.cmd_tree.children["tcs"].add_child(pt1000_node)
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── update_cfg{os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  │  └── set_param{os.linesep}"
                f"│  └── pt1000_0{os.linesep}"
                f"│     └── set_mode{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def _build_tree_with_hidden_children(self):
        self.base_tree()
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        mgm_0_node = CmdTreeNode("mgm_0", "MGM 0", hide_children_for_print=True)
        self.cmd_tree.children["acs"].add_child(mgm_0_node)
        update_cfg = CmdTreeNode("update_cfg", "Update Configuration")
        self.cmd_tree.children["acs"]["mgm_0"].add_child(update_cfg)
        tcs_ctrl = CmdTreeNode(
            "tcs_ctrl", "TCS Controller", hide_children_for_print=True
        )
        tcs_ctrl.add_child(CmdTreeNode("set_param", "Set Parameter"))
        self.cmd_tree.children["tcs"].add_child(tcs_ctrl)
        pt1000_node = CmdTreeNode("pt1000_0", "PT1000 0", hide_children_for_print=True)
        pt1000_node.add_child(CmdTreeNode("set_mode", "Set Mode"))
        pt1000_node.add_child(CmdTreeNode("set_cfg", "Set Config"))
        self.cmd_tree.children["tcs"].add_child(pt1000_node)
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))

    def test_printout_hidden_children(self):
        self._build_tree_with_hidden_children()
        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── ... (cut-off, children are hidden){os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  │  └── ... (cut-off, children are hidden){os.linesep}"
                f"│  └── pt1000_0{os.linesep}"
                f"│     └── ... (cut-off, children are hidden){os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def test_printout_hidden_override(self):
        self._build_tree_with_hidden_children()
        print(self.cmd_tree)
        printout = self.cmd_tree.str_for_tree(
            with_description=False, max_depth=None, show_hidden_elements=True
        )
        print(printout)
        self.assertEqual(
            printout,
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── update_cfg{os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  │  └── set_param{os.linesep}"
                f"│  └── pt1000_0{os.linesep}"
                f"│     ├── set_mode{os.linesep}"
                f"│     └── set_cfg{os.linesep}"
                f"└── ping{os.linesep}"
            ),
        )

    def _build_tree_with_suppressed_leaves(self):
        self.cmd_tree.children["acs"].add_child(
            CmdTreeNode("acs_ctrl", "ACS Controller")
        )
        mgm_0_node = CmdTreeNode("mgm_0", "MGM 0")
        self.cmd_tree.children["acs"].add_child(mgm_0_node)
        update_cfg = CmdTreeNode("update_cfg", "Update Configuration")
        self.cmd_tree.children["acs"]["mgm_0"].add_child(update_cfg)
        tcs_ctrl = CmdTreeNode(
            "tcs_ctrl", "TCS Controller", hide_children_for_print=True
        )
        tcs_ctrl.add_child(CmdTreeNode("set_param", "Set Parameter"))
        self.cmd_tree.children["tcs"].add_child(tcs_ctrl)
        pt1000_node = CmdTreeNode("pt1000_0", "PT1000 0", hide_children_for_print=True)
        pt1000_node.add_child(CmdTreeNode("set_mode", "Set Mode"))
        self.cmd_tree.children["tcs"].add_child(pt1000_node)
        self.cmd_tree.children["tcs"].add_child(CmdTreeNode("heaters", "Heaters"))
        self.cmd_tree.add_child(CmdTreeNode("ping", "Ping Command"))
        self.cmd_tree.children["acs"].hide_children_which_are_leaves = True
        self.cmd_tree.children["tcs"].hide_children_which_are_leaves = True
        self.cmd_tree["ping"].hide_children_which_are_leaves = True
        self.cmd_tree["ping"].add_child(CmdTreeNode("event", "Event Test"))
        self.cmd_tree["ping"]["event"].add_child(CmdTreeNode("0", "Event 0"))

    def test_printout_suppressed_leaves(self):
        self.base_tree()
        self._build_tree_with_suppressed_leaves()
        print(self.cmd_tree)
        self.assertEqual(
            str(self.cmd_tree),
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── mgm_0{os.linesep}"
                f"│  │  └── update_cfg{os.linesep}"
                f"│  └── ... (cut-off, leaves are hidden){os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  │  └── ... (cut-off, children are hidden){os.linesep}"
                f"│  ├── pt1000_0{os.linesep}"
                f"│  │  └── ... (cut-off, children are hidden){os.linesep}"
                f"│  └── ... (cut-off, leaves are hidden){os.linesep}"
                f"└── ping{os.linesep}"
                f"   └── event{os.linesep}"
                f"      └── 0{os.linesep}"
            ),
        )

    def test_printout_suppressed_leaves_print_override(self):
        self.base_tree()
        self._build_tree_with_suppressed_leaves()
        printout = self.cmd_tree.str_for_tree(
            False, max_depth=None, show_hidden_elements=True
        )
        print(printout)
        self.assertEqual(
            printout,
            (
                f"/{os.linesep}"
                f"├── acs{os.linesep}"
                f"│  ├── acs_ctrl{os.linesep}"
                f"│  └── mgm_0{os.linesep}"
                f"│     └── update_cfg{os.linesep}"
                f"├── tcs{os.linesep}"
                f"│  ├── tcs_ctrl{os.linesep}"
                f"│  │  └── set_param{os.linesep}"
                f"│  ├── pt1000_0{os.linesep}"
                f"│  │  └── set_mode{os.linesep}"
                f"│  └── heaters{os.linesep}"
                f"└── ping{os.linesep}"
                f"   └── event{os.linesep}"
                f"      └── 0{os.linesep}"
            ),
        )
