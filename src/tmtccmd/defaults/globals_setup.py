import argparse
import pprint

from tmtccmd.core.definitions import CoreGlobalIds, CoreComInterfaces, CoreModeList, CoreServiceList
from tmtccmd.defaults.com_setup import default_set_up_ethernet_cfg, default_set_up_serial_cfg
from tmtccmd.core.globals_manager import update_global
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


def default_add_globals_pre_args_parsing(gui: bool = False):
    from tmtccmd.core.globals_manager import update_global
    set_default_globals_pre_args_parsing(apid=0xef)
    if gui:
        default_set_up_ethernet_cfg()

    service_dict = get_core_service_dict()
    update_global(CoreGlobalIds.CURRENT_SERVICE, CoreServiceList.SERVICE_17)
    update_global(CoreGlobalIds.SERVICE_DICT, service_dict)


def default_add_globals_post_args_parsing(args: argparse.Namespace):
    mode_param = CoreModeList.ListenerMode
    if 0 <= args.mode <= 6:
        if args.mode == 0:
            mode_param = CoreModeList.GUIMode
        elif args.mode == 1:
            mode_param = CoreModeList.ListenerMode
        elif args.mode == 2:
            mode_param = CoreModeList.SingleCommandMode
        elif args.mode == 3:
            mode_param = CoreModeList.SequentialMode
        elif args.mode == 4:
            mode_param = CoreModeList.SoftwareTestMode
    update_global(CoreGlobalIds.MODE, mode_param)

    if args.com_if == CoreComInterfaces.EthernetUDP.value:
        com_if = CoreComInterfaces.EthernetUDP
    elif args.com_if == CoreComInterfaces.Serial:
        com_if = CoreComInterfaces.Serial
    elif args.com_if == CoreComInterfaces.Dummy:
        com_if = CoreComInterfaces.Dummy
    elif args.com_if == CoreComInterfaces.QEMU:
        com_if = CoreComInterfaces.QEMU
    else:
        com_if = CoreComInterfaces.Serial
    update_global(CoreGlobalIds.COM_IF, com_if)

    if args.short_display_mode:
        display_mode_param = "short"
    else:
        display_mode_param = "long"
    update_global(CoreGlobalIds.DISPLAY_MODE, display_mode_param)

    service = str(args.service).lower()
    if service == "2":
        service = CoreServiceList.SERVICE_2
    elif service == "3":
        service = CoreServiceList.SERVICE_3
    elif service == "5":
        service = CoreServiceList.SERVICE_5
    elif service == "8":
        service = CoreServiceList.SERVICE_8
    elif service == "9":
        service = CoreServiceList.SERVICE_9
    elif service == "17":
        service = CoreServiceList.SERVICE_17
    elif service == "20":
        service = CoreServiceList.SERVICE_20
    elif service == "23":
        service = CoreServiceList.SERVICE_23
    else:
        LOGGER.warning("Service not known! Setting standard service 17")
        service = CoreServiceList.SERVICE_17

    update_global(CoreGlobalIds.CURRENT_SERVICE, service)

    if args.op_code is None:
        op_code = 0
    else:
        op_code = str(args.op_code).lower()
    update_global(CoreGlobalIds.OP_CODE, op_code)

    update_global(CoreGlobalIds.USE_LISTENER_AFTER_OP, args.listener)
    update_global(CoreGlobalIds.TM_TIMEOUT, args.tm_timeout)
    update_global(CoreGlobalIds.PRINT_HK, args.print_hk)
    update_global(CoreGlobalIds.PRINT_TM, args.print_tm)
    update_global(CoreGlobalIds.PRINT_RAW_TM, args.raw_data_print)
    update_global(CoreGlobalIds.PRINT_TO_FILE, args.print_log)
    update_global(CoreGlobalIds.RESEND_TC, args.resend_tc)
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, 3)

    use_serial_cfg = False
    if com_if == CoreComInterfaces.Serial or com_if == CoreComInterfaces.QEMU:
        use_serial_cfg = True
    if use_serial_cfg:
        default_set_up_serial_cfg(com_if)

    use_ethernet_cfg = False
    if com_if == CoreComInterfaces.EthernetUDP:
        use_ethernet_cfg = True
    if use_ethernet_cfg:
        # TODO: Port and IP address can also be passed as CLI parameters. Use them here if applicable
        default_set_up_ethernet_cfg()


def get_core_service_dict() -> dict:
    core_service_dict = dict()
    core_service_dict[CoreServiceList.SERVICE_2] = ["Service 2 Raw Commanding"]
    core_service_dict[CoreServiceList.SERVICE_3] = ["Service 3 Housekeeping"]
    core_service_dict[CoreServiceList.SERVICE_5] = ["Service 5 Event"]
    core_service_dict[CoreServiceList.SERVICE_8] = ["Service 8 Functional Commanding"]
    core_service_dict[CoreServiceList.SERVICE_9] = ["Service 9 Time"]
    core_service_dict[CoreServiceList.SERVICE_17] = ["Service 17 Test"]
    core_service_dict[CoreServiceList.SERVICE_20] = ["Service 20 Parameters"]
    core_service_dict[CoreServiceList.SERVICE_23] = ["Service 23 File Management"]
    core_service_dict[CoreServiceList.SERVICE_200] = ["Service 200 Mode Management"]
    return core_service_dict


def set_default_globals_pre_args_parsing(
        apid: int, com_if_id: int = CoreComInterfaces.EthernetUDP, display_mode="long",
        tm_timeout: float = 4.0, print_to_file: bool = True, tc_send_timeout_factor: float = 2.0
):
    update_global(CoreGlobalIds.APID, apid)
    update_global(CoreGlobalIds.COM_IF, com_if_id)
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, tc_send_timeout_factor)
    update_global(CoreGlobalIds.TM_TIMEOUT, tm_timeout)
    update_global(CoreGlobalIds.DISPLAY_MODE, display_mode)
    update_global(CoreGlobalIds.PRINT_TO_FILE, print_to_file)
    update_global(CoreGlobalIds.SERIAL_CONFIG, dict())
    update_global(CoreGlobalIds.ETHERNET_CONFIG, dict())
    pp = pprint.PrettyPrinter()
    update_global(CoreGlobalIds.PRETTY_PRINTER, pp)
    update_global(CoreGlobalIds.TM_LISTENER_HANDLE, None)
    update_global(CoreGlobalIds.COM_INTERFACE_HANDLE, None)
    update_global(CoreGlobalIds.TMTC_PRINTER_HANDLE, None)
    update_global(CoreGlobalIds.PRINT_RAW_TM, False)
    update_global(CoreGlobalIds.RESEND_TC, False)
    update_global(CoreGlobalIds.OP_CODE, "0")
    update_global(CoreGlobalIds.MODE, CoreModeList.ListenerMode)
