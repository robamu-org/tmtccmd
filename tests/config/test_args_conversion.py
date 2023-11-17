import argparse
from unittest import TestCase

from tests.hook_obj_mock import create_hook_mock

from spacepackets.cfdp import TransmissionMode
from tmtccmd import CoreModeList, CoreModeConverter
from tmtccmd.config import CfdpParams
from tmtccmd.config.args import (
    args_to_all_params_tmtc,
    cfdp_args_to_cfdp_params,
    SetupParams,
    DefaultProcedureParams,
)


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
