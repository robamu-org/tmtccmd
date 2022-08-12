import argparse
from unittest import TestCase
from unittest.mock import MagicMock

from tests.hook_obj_mock import create_hook_mock
from tmtccmd import CoreModeList, CoreModeConverter, TmTcCfgHookBase
from tmtccmd.config.args import args_to_params, SetupParams, add_default_mode_arguments


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
        args_to_params(self.pargs, self.params, self.hook_mock, False)
        # Set to default value
        self.assertEqual(self.params.tc_params.delay, 3.0)
        # Unset
        self.assertEqual(self.params.tc_params.apid, 0)
        self.assertEqual(self.params.app_params.use_gui, False)
        self.assertEqual(self.params.app_params.use_ansi_colors, True)
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE),
        )
        self.assertEqual(self.params.backend_params.listener, False)
        self.assertEqual(self.params.backend_params.com_if_id, "dummy")

    def test_delay_set(self):
        self.simple_pargs_cli_set()
        self.pargs.delay = 2.0
        args_to_params(self.pargs, self.params, self.hook_mock, False)
        self.assertEqual(self.params.tc_params.delay, 2.0)

    def test_auto_listener_mode(self):
        self.auto_listener_cli_set()
        args_to_params(self.pargs, self.params, self.hook_mock, False)
        self.assertEqual(self.params.backend_params.listener, True)
        self.assertEqual(
            self.params.backend_params.mode,
            CoreModeConverter.get_str(CoreModeList.LISTENER_MODE),
        )
        self.assertEqual(
            self.params.mode, CoreModeConverter.get_str(CoreModeList.LISTENER_MODE)
        )
        self.params = SetupParams()
