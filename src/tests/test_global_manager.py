from unittest import TestCase
from tmtccmd.config.globals import update_global, get_global, get_global_apid, set_default_apid, \
    set_json_cfg_path, get_json_cfg_path, set_glob_com_if_dict, get_glob_com_if_dict, \
    set_default_globals_pre_args_parsing, check_and_set_core_mode_arg, CoreModeList, \
    CoreGlobalIds


class TestGlobalManager(TestCase):

    def test_global_module(self):
        update_global(global_param_id=30, parameter='hello')
        self.assertTrue(get_global(global_param_id=30) == 'hello')

        current_apid = get_global_apid()
        set_default_apid(default_apid=0x01)
        self.assertTrue(get_global_apid() == 0x01)
        set_default_apid(current_apid)

        current_path = get_json_cfg_path()
        set_json_cfg_path('.')
        self.assertTrue(get_json_cfg_path() == '.')
        set_json_cfg_path(current_path)

        custom_com_if_dict = {
            "test": ("Test Interface", "")
        }
        set_glob_com_if_dict(custom_com_if_dict=custom_com_if_dict)
        com_if_dict = get_glob_com_if_dict()
        self.assertTrue(com_if_dict["test"][0] == "Test Interface")

        set_default_globals_pre_args_parsing(
            gui=False, apid=0x02
        )
        self.assertTrue(get_global_apid() == 0x02)
        set_default_apid(current_apid)

        result = check_and_set_core_mode_arg(mode_arg='udp')
        self.assertTrue(result == CoreModeList.SEQUENTIAL_CMD_MODE)

        result = check_and_set_core_mode_arg(mode_arg='listener')
        self.assertTrue(get_global(CoreGlobalIds.MODE) == CoreModeList.LISTENER_MODE)
        self.assertTrue(result == CoreModeList.LISTENER_MODE)

        result = check_and_set_core_mode_arg(mode_arg='seqcmd')
        self.assertTrue(get_global(CoreGlobalIds.MODE) == CoreModeList.SEQUENTIAL_CMD_MODE)
        self.assertTrue(result == CoreModeList.SEQUENTIAL_CMD_MODE)
