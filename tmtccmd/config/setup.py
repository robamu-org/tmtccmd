from typing import Optional

from tmtccmd import TmTcCfgHookBase
from tmtccmd.config import default_json_path
from tmtccmd.config.args import ArgParserWrapper


class SetupArgs:
    """This class encapsulates various important setup parameters required by tmtccmd components"""

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
        """
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param args_wrapper: Optional helper wrapper which contains CLI arguments.
        :param use_gui: Specify whether a GUI is used.
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
