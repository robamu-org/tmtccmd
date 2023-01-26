import enum
from tmtccmd.tc.pus_20_fsfw_params import *  # noqa: F401


class CustomSubservice(enum.IntEnum):
    TC_LOAD = 128
    TC_DUMP = 129
