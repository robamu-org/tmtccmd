from spacepackets.ecss import PusTelecommand, PusServices
from tmtccmd.pus.pus_11_tc_sched import Subservices


def __generic_param_less_tc_sched_cmd(subservice: int) -> PusTelecommand:
    return PusTelecommand(service=PusServices.S11_TC_SCHED, subservice=subservice)


def generate_enable_tc_sched_cmd() -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(subservice=Subservices.TC_ENABLE)


def generate_disable_tc_sched_cmd() -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(subservice=Subservices.TC_DISABLE)


def generate_reset_tc_sched_cmd() -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(subservice=Subservices.TC_RESET)


def generate_time_tagged_cmd(release_time: bytes, tc_to_insert: PusTelecommand):
    return PusTelecommand(
        service=PusServices.S11_TC_SCHED,
        subservice=Subservices.TC_INSERT,
        app_data=pack_time_tagged_tc_app_data(release_time, tc_to_insert),
    )


def pack_time_tagged_tc_app_data(
    release_time: bytes, tc_to_insert: PusTelecommand
) -> bytes:
    """This function packs another TC into an insert activity TC[11,4]
    :param release_time: Absolute time when TC shall be released/run
    :param tc_to_insert: The TC which shall be inserted
    """
    app_data = bytearray()
    # pack the release time
    app_data.extend(release_time)
    # followed by the tc
    app_data.extend(tc_to_insert.pack())
    return app_data
