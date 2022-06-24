import argparse
from typing import Optional

from tmtccmd.config.globals import (
    CoreServiceList,
    handle_mode_arg,
    check_and_set_other_args,
    handle_com_if_arg,
)
from .definitions import (
    CoreGlobalIds,
    OpCodeDictKeys,
    default_json_path,
)
from .cfg_hook import TmTcCfgHookBase


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


"""
def pass_cli_args(
    setup_args: SetupArgs,
    custom_modes_list: Optional[List[Union[collections.abc.Iterable, Dict]]] = None,
    custom_com_if_dict: Dict[str, any] = None,
):

    logger = get_console_logger()
    args = setup_args.cli_args
    handle_mode_arg(args=args, custom_modes_list=custom_modes_list)
    handle_com_if_arg(
        args=args,
        json_cfg_path=setup_args.json_cfg_path,
        custom_com_if_dict=custom_com_if_dict,
    )

    display_mode_param = "long"
    if args.sh_display is not None:
        if args.sh_display:
            display_mode_param = "short"
        else:
            display_mode_param = "long"
    update_global(CoreGlobalIds.DISPLAY_MODE, display_mode_param)

    try:
        service_param = args.service
    except AttributeError:
        logger.warning(
            "Passed namespace does not contain the service (-s) argument. "
            "Setting test service ID (17)"
        )
        service_param = CoreServiceList.SERVICE_17.value
    update_global(CoreGlobalIds.CURRENT_SERVICE, service_param)

    if args.op_code is None:
        op_code = 0
    else:
        op_code = str(args.op_code).lower()
    update_global(CoreGlobalIds.OP_CODE, op_code)

    try:
        check_and_set_other_args(args=args)
    except AttributeError:
        logger.exception("Passed arguments are missing components.")

"""
