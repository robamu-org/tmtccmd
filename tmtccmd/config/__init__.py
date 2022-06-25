from typing import Optional

from tmtccmd.config.globals import CoreServiceList
from .args import ArgParserWrapper
from .definitions import (
    CoreGlobalIds,
    OpCodeDictKeys, default_json_path
)
from tmtccmd.config.cfg_hook import TmTcCfgHookBase


class SetupArgs:
    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        use_gui: bool,
        apid: int,
        args_wrapper: Optional[ArgParserWrapper],
        json_cfg_path: Optional[str] = None,
        reduced_printout: bool = False,
        use_ansi_colors: bool = True,
    ):
        """This class encapsulates all required objects for the TMTC commander
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param args_wrapper: Command line arguments as returned by the ArgumentParser.parse_args method
        :param use_gui: Specify whether a GUI is used
        :param reduced_printout:
        :param use_ansi_colors:
        """
        self.hook_obj = hook_obj
        self.use_gui = use_gui
        self.apid = apid
        self.json_cfg_path = json_cfg_path
        self.reduced_printout = reduced_printout
        self.ansi_colors = use_ansi_colors
        self.args_wrapper = args_wrapper
        self.json_cfg_path = json_cfg_path
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()
