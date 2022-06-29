import collections.abc
import enum
import pprint
from typing import Union, List, Dict

from spacepackets.ecss.conf import (
    set_default_tc_apid,
    set_default_tm_apid,
)

from tmtccmd.logging import get_console_logger
from tmtccmd.core.globals_manager import update_global, get_global
from tmtccmd.config import (
    CoreModeList,
    CoreServiceList,
    CoreModeStrings,
    CORE_COM_IF_DICT,
    CoreComInterfaces,
    ComIfDictT,
)
from tmtccmd.config.tmtc import TmTcDefWrapper, OpCodeEntry


LOGGER = get_console_logger()
DEF_WRAPPER = None


class CoreGlobalIds(enum.IntEnum):
    """
    Numbers from 128 to 200 are reserved for core globals
    """

    # Object handles
    TMTC_HOOK = 128
    COM_INTERFACE_HANDLE = 129
    TM_LISTENER_HANDLE = 130
    TMTC_PRINTER_HANDLE = 131
    TM_HANDLER_HANDLE = 132
    PRETTY_PRINTER = 133

    # Parameters
    JSON_CFG_PATH = 139
    MODE = 141
    CURRENT_SERVICE = 142
    COM_IF = 144
    OP_CODE = 145
    TM_TIMEOUT = 146
    SERVICE_OP_CODE_DICT = 147
    COM_IF_DICT = 148

    # Miscellaneous
    DISPLAY_MODE = 150
    USE_LISTENER_AFTER_OP = 151
    PRINT_HK = 152
    PRINT_TM = 153
    PRINT_RAW_TM = 154
    PRINT_TO_FILE = 155
    RESEND_TC = 156
    TC_SEND_TIMEOUT_FACTOR = 157

    # Config dictionaries
    USE_SERIAL = 160
    SERIAL_CONFIG = 161
    USE_ETHERNET = 162
    ETHERNET_CONFIG = 163
    END = 300


def set_json_cfg_path(json_cfg_path: str):
    update_global(CoreGlobalIds.JSON_CFG_PATH, json_cfg_path)


def get_json_cfg_path() -> str:
    return get_global(CoreGlobalIds.JSON_CFG_PATH)


def set_glob_com_if_dict(custom_com_if_dict: ComIfDictT):
    CORE_COM_IF_DICT.update(custom_com_if_dict)
    update_global(CoreGlobalIds.COM_IF_DICT, CORE_COM_IF_DICT)


def get_glob_com_if_dict() -> ComIfDictT:
    return get_global(CoreGlobalIds.COM_IF_DICT)


def set_default_globals_pre_args_parsing(
    apid: int,
    com_if_id: str = CoreComInterfaces.DUMMY.value,
    custom_com_if_dict=None,
    display_mode="long",
    tm_timeout: float = 4.0,
    print_to_file: bool = True,
    tc_send_timeout_factor: float = 2.0,
):
    if custom_com_if_dict is None:
        custom_com_if_dict = dict()
    set_default_tc_apid(tc_apid=apid)
    set_default_tm_apid(tm_apid=apid)
    update_global(CoreGlobalIds.COM_IF, com_if_id)
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, tc_send_timeout_factor)
    update_global(CoreGlobalIds.TM_TIMEOUT, tm_timeout)
    update_global(CoreGlobalIds.DISPLAY_MODE, display_mode)
    update_global(CoreGlobalIds.PRINT_TO_FILE, print_to_file)
    update_global(CoreGlobalIds.CURRENT_SERVICE, CoreServiceList.SERVICE_17.value)
    update_global(CoreGlobalIds.SERIAL_CONFIG, dict())
    update_global(CoreGlobalIds.ETHERNET_CONFIG, dict())
    set_glob_com_if_dict(custom_com_if_dict=custom_com_if_dict)
    pp = pprint.PrettyPrinter()
    update_global(CoreGlobalIds.PRETTY_PRINTER, pp)
    update_global(CoreGlobalIds.TM_LISTENER_HANDLE, None)
    update_global(CoreGlobalIds.COM_INTERFACE_HANDLE, None)
    update_global(CoreGlobalIds.TMTC_PRINTER_HANDLE, None)
    update_global(CoreGlobalIds.PRINT_RAW_TM, False)
    update_global(CoreGlobalIds.USE_LISTENER_AFTER_OP, True)
    update_global(CoreGlobalIds.RESEND_TC, False)
    update_global(CoreGlobalIds.OP_CODE, "0")
    update_global(CoreGlobalIds.MODE, CoreModeList.LISTENER_MODE)


def handle_mode_arg(
    args,
    custom_modes_list: Union[None, List[Union[collections.abc.Iterable, dict]]] = None,
) -> int:
    # Determine communication interface from arguments. Must be contained in core modes list
    try:
        mode_param = args.mode
    except AttributeError:
        LOGGER.warning("Passed namespace does not contain the mode (-m) argument")
        mode_param = CoreModeList.LISTENER_MODE
    mode_param = check_and_set_core_mode_arg(
        mode_arg=mode_param, custom_modes_list=custom_modes_list
    )
    update_global(CoreGlobalIds.MODE, mode_param)
    return mode_param


def handle_com_if_arg(
    args, json_cfg_path: str, custom_com_if_dict: Dict[str, any] = None
):
    from tmtccmd.com_if.utils import determine_com_if

    all_com_ifs = CORE_COM_IF_DICT
    if custom_com_if_dict is not None:
        all_com_ifs = CORE_COM_IF_DICT.update(custom_com_if_dict)
    try:
        com_if_key = str(args.com_if_id)
    except AttributeError:
        LOGGER.warning("No communication interface specified")
        LOGGER.warning("Trying to set from existing configuration..")
        com_if_key = determine_com_if(
            com_if_dict=all_com_ifs, json_cfg_path=json_cfg_path
        )
    if com_if_key == CoreComInterfaces.UNSPECIFIED.value:
        com_if_key = determine_com_if(
            com_if_dict=all_com_ifs, json_cfg_path=json_cfg_path
        )
    update_global(CoreGlobalIds.COM_IF, com_if_key)
    try:
        LOGGER.info(f"Communication interface: {all_com_ifs[com_if_key]}")
    except KeyError as e:
        LOGGER.error(f"Invalid communication interface key {com_if_key}, error {e}")


def check_and_set_other_args(args):
    if args.listener is not None:
        update_global(CoreGlobalIds.USE_LISTENER_AFTER_OP, args.listener)
    if args.tm_timeout is not None:
        update_global(CoreGlobalIds.TM_TIMEOUT, args.tm_timeout)
    if args.print_hk is not None:
        update_global(CoreGlobalIds.PRINT_HK, args.print_hk)
    if args.print_tm is not None:
        update_global(CoreGlobalIds.PRINT_TM, args.print_tm)
    if args.raw_print is not None:
        update_global(CoreGlobalIds.PRINT_RAW_TM, args.raw_print)
    if args.print_log is not None:
        update_global(CoreGlobalIds.PRINT_TO_FILE, args.print_log)
    if args.resend_tc is not None:
        update_global(CoreGlobalIds.RESEND_TC, args.resend_tc)
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, 3)


def check_and_set_core_mode_arg(
    mode_arg: any,
    custom_modes_list: Union[None, List[Union[dict, collections.abc.Iterable]]] = None,
) -> int:
    from tmtccmd.utility.conf_util import check_args_in_dict

    """Checks whether the mode argument is contained inside the core mode list integer enumeration
    or a custom mode list integer which can be passed optionally.
    This function will set the single command mode as the global mode parameter if the passed mode
    is not found in either enumerations.

    :param mode_arg:
    :param custom_modes_list:
    :return: Mode value which was set
    """
    in_enum, mode_value = check_args_in_dict(
        param=mode_arg, iterable=CoreModeList, warning_hint="mode integers"
    )
    if not in_enum:
        in_enum, mode_value = check_args_in_dict(
            param=mode_arg, iterable=CoreModeStrings, warning_hint="mode strings"
        )
    if in_enum:
        update_global(CoreGlobalIds.MODE, mode_value)
        return mode_value

    mode_arg_invalid = False
    if custom_modes_list is not None:
        for custom_mode_entry in custom_modes_list:
            in_enum, mode_value = check_args_in_dict(
                param=mode_arg, iterable=custom_mode_entry, warning_hint="custom mode"
            )
            if in_enum:
                break
        if not in_enum:
            mode_arg_invalid = True
    else:
        mode_arg_invalid = True

    if mode_arg_invalid:
        LOGGER.warning(
            f"Passed mode argument might be invalid, "
            f"setting to {CoreModeList.ONE_QUEUE_MODE}"
        )
        mode_value = CoreModeList.ONE_QUEUE_MODE
    update_global(CoreGlobalIds.MODE, mode_value)
    return mode_value


def check_and_set_core_service_arg(
    service_arg: any, custom_service_list: collections.abc.Iterable = None
):
    from tmtccmd.utility.conf_util import check_args_in_dict

    in_enum, service_value = check_args_in_dict(
        param=service_arg, iterable=CoreServiceList, warning_hint="service"
    )
    if in_enum:
        update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)
        return

    service_arg_invalid = False
    if custom_service_list is not None:
        for custom_services_entry in custom_service_list:
            in_enum, service_value = check_args_in_dict(
                param=service_arg,
                iterable=custom_services_entry,
                warning_hint="custom mode",
            )
            if in_enum:
                break
        if not in_enum:
            service_arg_invalid = True
    else:
        service_arg_invalid = True

    if service_arg_invalid:
        LOGGER.warning(
            f"Passed service argument might be invalid, "
            f"setting to {CoreServiceList.SERVICE_17}"
        )
        service_value = CoreServiceList.SERVICE_17
    update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)


def get_default_tmtc_defs() -> TmTcDefWrapper:
    global DEF_WRAPPER
    if DEF_WRAPPER is None:
        DEF_WRAPPER = TmTcDefWrapper()
        srv_5 = OpCodeEntry()
        srv_5.add("0", "Event Test")
        DEF_WRAPPER.add_service(
            service_name=CoreServiceList.SERVICE_5.value,
            info="PUS Service 5 Event",
            op_code_entry=srv_5,
        )
        srv_17 = OpCodeEntry()
        srv_17.add("0", "Ping Test")
        DEF_WRAPPER.add_service(
            service_name=CoreServiceList.SERVICE_17.value,
            info="PUS Service 17 Test",
            op_code_entry=srv_17,
        )
    return DEF_WRAPPER
