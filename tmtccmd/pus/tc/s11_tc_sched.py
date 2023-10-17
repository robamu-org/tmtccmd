import deprecation

from tmtccmd.version import get_version
from spacepackets.ecss import PusTelecommand, PusService
from tmtccmd.pus.s11_tc_sched import Subservice


def __generic_param_less_tc_sched_cmd(
    subservice: int, apid: int = 0, seq_count: int = 0
) -> PusTelecommand:
    return PusTelecommand(
        service=PusService.S11_TC_SCHED,
        subservice=subservice,
        apid=apid,
        seq_count=seq_count,
    )


@deprecation.deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_enable_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return create_enable_tc_sched_cmd(apid, seq_count)


def create_enable_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservice.TC_ENABLE, apid=apid, seq_count=seq_count
    )


@deprecation.deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_disable_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return create_disable_tc_sched_cmd(apid, seq_count)


def create_disable_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservice.TC_DISABLE, apid=apid, seq_count=seq_count
    )


@deprecation.deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_reset_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return create_reset_tc_sched_cmd(apid, seq_count)


def create_reset_tc_sched_cmd(apid: int = 0, seq_count: int = 0) -> PusTelecommand:
    return __generic_param_less_tc_sched_cmd(
        subservice=Subservice.TC_RESET, apid=apid, seq_count=seq_count
    )


@deprecation.deprecated(
    deprecated_in="4.0.0a2",
    current_version=get_version(),
    details="use create... API instead",
)
def generate_time_tagged_cmd(release_time: bytes, tc_to_insert: PusTelecommand):
    return create_time_tagged_cmd(release_time, tc_to_insert)


def create_time_tagged_cmd(
    release_time: bytes, tc_to_insert: PusTelecommand, apid: int = 0, seq_count: int = 0
):
    return PusTelecommand(
        service=PusService.S11_TC_SCHED,
        subservice=Subservice.TC_INSERT,
        app_data=pack_time_tagged_tc_app_data(release_time, tc_to_insert),
        apid=apid,
        seq_count=seq_count,
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
