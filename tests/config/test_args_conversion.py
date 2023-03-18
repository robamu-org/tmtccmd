import argparse
from unittest import TestCase

from tests.hook_obj_mock import create_hook_mock
from tmtccmd import CoreModeList, CoreModeConverter
from tmtccmd.config.args import args_to_params_tmtc, SetupParams, DefaultProcedureParams


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
        self.pargs.service = None
        self.pargs.op_code = None

    def simple_pargs_cli_set(self):
        self.base_cli_set()
        self.pargs.listener = False
        self.pargs.service = "17"
        self.pargs.op_code = "ping"

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
        def_params = DefaultProcedureParams()
        args_to_params_tmtc(
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
        self.assertEqual(def_params.service, "17")
        self.assertEqual(def_params.op_code, "ping")
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE),
        )
        self.assertEqual(self.params.backend_params.listener, False)
        self.assertEqual(self.params.backend_params.com_if_id, "dummy")

    def test_delay_set(self):
        self.simple_pargs_cli_set()
        self.pargs.delay = 2.0
        def_params = DefaultProcedureParams()
        args_to_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertEqual(def_params.service, "17")
        self.assertEqual(def_params.op_code, "ping")
        self.assertEqual(self.params.tc_params.delay, 2.0)

    def test_auto_listener_mode(self):
        self.auto_listener_cli_set()
        def_params = DefaultProcedureParams()
        args_to_params_tmtc(
            pargs=self.pargs,
            params=self.params,
            hook_obj=self.hook_mock,
            use_prompts=False,
            def_tmtc_params=def_params,
            assign_com_if=False,
        )
        self.assertEqual(self.params.backend_params.listener, True)
        self.assertIsNone(def_params.service)
        self.assertIsNone(def_params.op_code)
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.LISTENER_MODE),
        )
        self.assertEqual(
            self.params.mode, CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)
        )
        self.params = SetupParams()
