import argparse
import os
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from spacepackets.cfdp import TransmissionMode

from tests.hook_obj_mock import create_hook_mock
from tmtccmd import CoreModeConverter, CoreModeList
from tmtccmd.config import CfdpParams
from tmtccmd.config.args import (
    AppParams,
    DefaultProcedureParams,
    SetupParams,
    args_to_all_params_tmtc,
    cfdp_args_to_cfdp_params,
    perform_tree_printout,
)
from tmtccmd.config.tmtc import CmdTreeNode, TreePart


class TestArgs(TestCase):
    def setUp(self) -> None:
        self.pargs = argparse.Namespace()
        self.params = SetupParams()
        self.hook_mock = create_hook_mock()

    def base_cli_set(self):
        self.pargs.gui = None
        self.pargs.mode = None
        self.pargs.delay = None
        self.pargs.com_if = "dummy"
        self.pargs.listener = True
        self.pargs.prompt_proc = False
        self.pargs.cmd_path = None
        self.pargs.print_tree = None

    def simple_pargs_cli_set(self):
        self.base_cli_set()
        self.pargs.listener = False
        self.pargs.cmd_path = "/PING"

    def auto_listener_cli_set(self):
        self.base_cli_set()
        self.pargs.listener = True

    def test_basic(self):
        # For some reason, those fields need to be reset manually
        self.params.backend_params.mode = ""
        self.params.backend_params.com_if_id = ""
        self.simple_pargs_cli_set()
        self.assertEqual(self.params.tc_params.delay, 0)
        self.assertEqual(self.params.backend_params.mode, "")
        self.assertEqual(self.params.backend_params.com_if_id, "")
        def_params = DefaultProcedureParams(None)
        args_to_all_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        # Set to default value
        self.assertEqual(self.params.tc_params.delay, 4.0)
        # Unset
        self.assertEqual(self.params.tc_params.apid, 0)
        self.assertEqual(self.params.app_params.use_gui, False)
        self.assertEqual(self.params.app_params.use_ansi_colors, True)
        self.assertEqual(def_params.cmd_path, "/PING")
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE),
        )
        self.assertEqual(self.params.backend_params.listener, False)
        self.assertEqual(self.params.backend_params.com_if_id, "dummy")

    def test_delay_set(self):
        self.simple_pargs_cli_set()
        self.pargs.delay = 2.0
        def_params = DefaultProcedureParams(None)
        args_to_all_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertEqual(def_params.cmd_path, "/PING")
        self.assertEqual(self.params.tc_params.delay, 2.0)

    def test_cfdp_conversion_basic(self):
        self.pargs.source = "hello.txt"
        self.pargs.target = "hello-dest.txt"
        self.pargs.no_closure = False
        self.pargs.proxy = True
        self.pargs.type = "nak"
        cfdp_params = CfdpParams()
        cfdp_params.transmission_mode = TransmissionMode.ACKNOWLEDGED
        self.assertEqual(cfdp_params.closure_requested, False)
        self.assertEqual(cfdp_params.proxy_op, False)
        cfdp_args_to_cfdp_params(self.pargs, cfdp_params)
        self.assertEqual(cfdp_params.source_file, "hello.txt")
        self.assertEqual(cfdp_params.dest_file, "hello-dest.txt")
        self.assertEqual(cfdp_params.closure_requested, True)
        self.assertEqual(cfdp_params.transmission_mode, TransmissionMode.UNACKNOWLEDGED)
        self.assertEqual(cfdp_params.proxy_op, True)

    def test_cfdp_conversion_acked(self):
        self.pargs.type = "ack"
        cfdp_params = CfdpParams()
        cfdp_args_to_cfdp_params(self.pargs, cfdp_params)
        self.assertEqual(cfdp_params.transmission_mode, TransmissionMode.ACKNOWLEDGED)

    def test_auto_listener_mode(self):
        self.auto_listener_cli_set()
        def_params = DefaultProcedureParams(None)
        args_to_all_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertEqual(self.params.backend_params.listener, True)
        self.assertIsNone(def_params.cmd_path)
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.LISTENER_MODE),
        )
        self.assertEqual(
            self.params.mode, CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)
        )
        self.params = SetupParams()

    def test_tree_printout_conversion_default(self):
        self.base_cli_set()
        self.pargs.print_tree = []
        def_params = DefaultProcedureParams(None)
        args_to_all_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertTrue(self.params.app_params.print_tree)
        self.assertTrue(self.params.app_params.tree_print_with_description)
        self.assertIsNone(self.params.app_params.tree_print_max_depth)

    def test_tree_printout_conversion_with_custom_args(self):
        self.base_cli_set()
        self.pargs.print_tree = ["b", "2"]
        def_params = DefaultProcedureParams(None)
        args_to_all_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertTrue(self.params.app_params.print_tree)
        self.assertFalse(self.params.app_params.tree_print_with_description)
        self.assertEqual(self.params.app_params.tree_print_max_depth, 2)

    @patch("builtins.print")
    def test_tree_printout_0(self, print_mock: MagicMock):
        root_node_only = CmdTreeNode.root_node()
        app_params = AppParams()
        app_params.print_tree = True
        perform_tree_printout(app_params, root_node_only)
        self.assertEqual(len(print_mock.call_args_list), 2)
        self.assertEqual(
            print_mock.call_args_list[0],
            call("Printing command tree with full descriptions:"),
        )
        printout = print_mock.call_args_list[1].args[0]
        self.assertTrue("/" in printout)
        self.assertTrue("[ Root Node ]" in printout)

    @patch("builtins.print")
    def test_tree_printout_1(self, print_mock: MagicMock):
        root_node_only = CmdTreeNode.root_node()
        app_params = AppParams()
        app_params.print_tree = True
        app_params.tree_print_with_description = False
        perform_tree_printout(app_params, root_node_only)
        self.assertEqual(len(print_mock.call_args_list), 2)
        self.assertEqual(
            print_mock.call_args_list[0],
            call("Printing command tree without descriptions:"),
        )
        self.assertEqual(print_mock.call_args_list[1], call(f"/{os.linesep}"))

    @patch("builtins.print")
    def test_tree_printout_2(self, print_mock: MagicMock):
        root_node_only = CmdTreeNode.root_node()
        root_node_only.add_child(CmdTreeNode("acs", "ACS Subsystem"))
        app_params = AppParams()
        app_params.print_tree = True
        app_params.tree_print_with_description = False
        app_params.tree_print_max_depth = 0
        perform_tree_printout(app_params, root_node_only)
        self.assertEqual(len(print_mock.call_args_list), 2)
        self.assertEqual(
            print_mock.call_args_list[0],
            call("Printing command tree without descriptions and maximum depth 0:"),
        )
        self.assertEqual(
            print_mock.call_args_list[1],
            call(
                f"/{os.linesep}{TreePart.CORNER.value} ... (cut-off, maximum depth 0){os.linesep}"
            ),
        )
