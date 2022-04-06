from unittest import TestCase
from tmtccmd.ccsds.handler import CcsdsTmHandler
import tmtccmd.runner as tmtccmd

from tests.backend_mock import create_backend_mock, create_frontend_mock
from tests.hook_obj_mock import create_hook_mock


class TestTmtcRunner(TestCase):
    def test_tmtc_runner(self):
        # TODO: Update tests for updated API
        """
        hook_base = create_hook_mock()
        tm_handler = CcsdsTmHandler()
        init_tmtccmd(hook_object=hook_base)
        setup_tmtccmd(use_gui=False, reduced_printout=False)
        backend_mock = create_backend_mock(tm_handler=tm_handler)
        run_tmtccmd(tmtc_backend=backend_mock)
        backend_mock.start_listener.assert_called_with()
        backend_mock.initialize.assert_called_with()
        """

        # TODO: Maybe we can remove this test altogether..
        """
        frontend_mock = create_frontend_mock()
        run_tmtccmd(
            use_gui=True,
            tmtc_backend=backend_mock,
            tmtc_frontend=frontend_mock,
        )
        frontend_mock.start.assert_called_once()
        qt_app = frontend_mock.start.call_args[0][0]
        # TODO: Fix test
        # self.assertTrue(qt_app is None)

        default_backend = get_default_tmtc_backend(
        hook_obj=hook_base, tm_handler=tm_handler, json_cfg_path="tmtc_config.json"
        )
        self.assertTrue(default_backend is not None)
        """

    def test_errors(self):
        # TODO: API has changed, update tests
        # self.assertRaises(ValueError, init_tmtccmd, None)
        # self.assertRaises(TypeError, run_tmtccmd)
        # self.assertRaises(RuntimeError, run_tmtccmd, False)
        pass
