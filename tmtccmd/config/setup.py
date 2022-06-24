import argparse
from typing import Optional

from tmtccmd.config import TmTcCfgHookBase, default_json_path


class SetupArgs:
    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        use_gui: bool,
        apid: int,
        cli_args: Optional[argparse.Namespace],
        json_cfg_path: Optional[str] = None,
        reduced_printout: bool = False,
        use_ansi_colors: bool = True,
    ):
        """This class encapsulates all required objects for the TMTC commander
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param cli_args: Command line arguments as returned by the ArgumentParser.parse_args method
        :param use_gui: Specify whether a GUI is used
        :param reduced_printout:
        :param use_ansi_colors:
        """
        self.hook_obj = hook_obj
        self.use_gui = use_gui
        self.json_cfg_path = json_cfg_path
        self.reduced_printout = reduced_printout
        self.ansi_colors = use_ansi_colors
        self.cli_args = cli_args
        self.json_cfg_path = json_cfg_path
        self.tc_apid = apid
        self.tm_apid = apid
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()
