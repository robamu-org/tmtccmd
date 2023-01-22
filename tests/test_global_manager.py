from unittest import TestCase
from tmtccmd.config.globals import (
    update_global,
    get_global,
    set_json_cfg_path,
    get_json_cfg_path,
    set_glob_com_if_dict,
    get_glob_com_if_dict,
    set_default_globals_pre_args_parsing,
)
from tmtccmd.core.globals_manager import (
    lock_global_pool,
    unlock_global_pool,
    set_lock_timeout,
)


class TestGlobalManager(TestCase):
    def test_global_module(self):
        update_global(global_param_id=30, parameter="hello")
        self.assertTrue(get_global(global_param_id=30) == "hello")

        current_path = get_json_cfg_path()
        set_json_cfg_path(".")
        self.assertTrue(get_json_cfg_path() == ".")
        set_json_cfg_path(current_path)

        custom_com_if_dict = {"test": ("Test Interface", "")}
        set_glob_com_if_dict(custom_com_if_dict=custom_com_if_dict)
        com_if_dict = get_glob_com_if_dict()
        self.assertTrue(com_if_dict["test"][0] == "Test Interface")

        set_default_globals_pre_args_parsing(apid=0x02)

        lock_global_pool()
        unlock_global_pool()
        set_lock_timeout(0.5)
