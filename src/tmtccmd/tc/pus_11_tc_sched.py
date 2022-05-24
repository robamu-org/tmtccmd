from spacepackets.ecss import PusTelecommand
from tmtccmd.pus.definitions import PusServices
from tmtccmd.pus.pus_11_tc_sched import Subservices


def generate_enable_tc_sched_cmd(ssc: int, apid: int = -1) -> PusTelecommand:
    return PusTelecommand(
        service=PusServices.S11_TC_SCHED,
        subservice=Subservices.TC_ENABLE,
        ssc=ssc,
        apid=apid
    )
