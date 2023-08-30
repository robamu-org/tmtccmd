import collections.abc
import enum
import logging
import pprint

import deprecation
from spacepackets.ecss.conf import (
    set_default_tc_apid,
    set_default_tm_apid,
)

from tmtccmd.core.globals_manager import update_global, get_global
from tmtccmd.config.defs import (
    CoreModeList,
    CoreServiceList,
    CORE_COM_IF_DICT,
    CoreComInterfaces,
    ComIfDictT,
)
from tmtccmd.config.tmtc import TmtcDefinitionWrapper
from tmtccmd.version import get_version

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


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
def set_json_cfg_path(json_cfg_path: str):
    update_global(CoreGlobalIds.JSON_CFG_PATH, json_cfg_path)


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
def get_json_cfg_path() -> str:
    return get_global(CoreGlobalIds.JSON_CFG_PATH)


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
def set_glob_com_if_dict(custom_com_if_dict: ComIfDictT):
    CORE_COM_IF_DICT.update(custom_com_if_dict)
    update_global(CoreGlobalIds.COM_IF_DICT, CORE_COM_IF_DICT)


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
def get_glob_com_if_dict() -> ComIfDictT:
    return get_global(CoreGlobalIds.COM_IF_DICT)


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
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


@deprecation.deprecated(deprecated_in="6.0.0rc0", current_version=get_version())
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


def check_and_set_core_service_arg(
    service_arg: any, custom_service_list: collections.abc.Iterable = None
):
    from tmtccmd.util.conf_util import check_args_in_dict

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
        logging.getLogger(__name__).warning(
            f"Passed service argument might be invalid, "
            f"setting to {CoreServiceList.SERVICE_17}"
        )
        service_value = CoreServiceList.SERVICE_17
    update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)


def get_default_tmtc_defs() -> TmtcDefinitionWrapper:
    global DEF_WRAPPER
    if DEF_WRAPPER is None:
        DEF_WRAPPER = TmtcDefinitionWrapper()
    return DEF_WRAPPER
