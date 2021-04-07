import collections

from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.conf_util import check_args_in_enum
from tmtccmd.core.definitions import CoreGlobalIds, CoreModeList, CoreComInterfaces, CoreServiceList
from tmtccmd.core.globals_manager import update_global


LOGGER = get_logger()


def set_hk_handling_for_custom_hk_format():
    update_global(CoreGlobalIds.CUSTOM_HK_REPORT_FORMAT, True)


def check_and_set_core_mode_arg(mode_arg: any, custom_mode_int_enum: collections.Iterable = None):
    """
    Checks whether the mode argument is contained inside the core mode list integer enumeration
    or a custom mode list integer which can be passed optionally.
    This function will set the single command mode as the global mode parameter if the passed mode
    is not found in either enumerations.
    :param mode_arg:
    :param custom_mode_int_enum:
    :return:
    """
    in_enum, mode_value = check_args_in_enum(
        param=mode_arg, enumeration=CoreModeList, warning_hint="mode"
    )
    if in_enum:
        update_global(CoreGlobalIds.MODE, mode_value)
        return

    mode_arg_invalid = False
    if custom_mode_int_enum is not None:
        in_enum, mode_value = check_args_in_enum(
            param=mode_arg, enumeration=custom_mode_int_enum, warning_hint="custom mode"
        )
        if not in_enum:
            mode_arg_invalid = True
    else:
        mode_arg_invalid = True

    if mode_arg_invalid:
        LOGGER.warning(f"Passed mode argument might be invalid, "
                       f"setting to {CoreModeList.SINGLE_CMD_MODE}")
        mode_value = CoreModeList.SINGLE_CMD_MODE
    update_global(CoreGlobalIds.MODE, mode_value)


def check_and_set_core_com_if_arg(com_if_arg: any, custom_com_if_list: collections.Iterable = None):
    in_enum, com_if_value = check_args_in_enum(
        param=com_if_arg, enumeration=CoreComInterfaces, warning_hint="communication interface"
    )
    if in_enum:
        update_global(CoreGlobalIds.COM_IF, com_if_value)
        return

    com_if_arg_invalid = False
    if custom_com_if_list is not None:
        in_enum, com_if_value = check_args_in_enum(
            param=com_if_arg, enumeration=custom_com_if_list,
            warning_hint="custom communication interface"
        )
        if not in_enum:
            com_if_arg_invalid = True
    else:
        com_if_arg_invalid = True

    if com_if_arg_invalid:
        LOGGER.warning(f"Passed communication interface argument might be invalid, "
                       f"setting to {CoreComInterfaces.DUMMY}")
        com_if_value = CoreComInterfaces.DUMMY
    update_global(CoreGlobalIds.COM_IF, com_if_value)


def check_and_set_core_service_arg(
        service_arg: any, custom_service_list: collections.Iterable = None
):
    in_enum, service_value = check_args_in_enum(
        param=service_arg, enumeration=CoreServiceList, warning_hint="service"
    )
    if in_enum:
        update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)
        return

    service_arg_invalid = False
    if custom_service_list is not None:
        in_enum, service_value = check_args_in_enum(
            param=service_arg, enumeration=custom_service_list, warning_hint="custom mode"
        )
        if not in_enum:
            service_arg_invalid = True
    else:
        service_arg_invalid = True

    if service_arg_invalid:
        LOGGER.warning(f"Passed service argument might be invalid, "
                       f"setting to {CoreServiceList.SERVICE_17}")
        service_value = CoreServiceList.SERVICE_17
    update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)
