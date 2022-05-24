from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.conf import FETCH_GLOBAL_APID
from tmtccmd.pus.definitions import PusServices
from tmtccmd.pus.pus_11_tc_sched import Subservices


def __generic_param_less_tc_sched_cmd(
    subservice: int, ssc: int, apid: int = -1
) -> PusTelecommand:
    return PusTelecommand(
        service=PusServices.S11_TC_SCHED, subservice=subservice, ssc=ssc, apid=apid
    )


def generate_enable_tc_sched_cmd(
    ssc: int, apid: int = FETCH_GLOBAL_APID
) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservices.TC_ENABLE, ssc=ssc, apid=apid
    )


def generate_disable_tc_sched_cmd(
    ssc: int, apid: int = FETCH_GLOBAL_APID
) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservices.TC_DISABLE, ssc=ssc, apid=apid
    )


def generate_reset_tc_sched_cmd(
    ssc: int, apid: int = FETCH_GLOBAL_APID
) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservices.TC_RESET, ssc=ssc, apid=apid
    )
