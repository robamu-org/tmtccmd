from __future__ import annotations

import struct
from collections import deque

from spacepackets.ecss.pus_1_verification import (
    Service1Tm,
)


class Service1FsfwWrapper:
    def __init__(self, tm: Service1Tm):
        self.tm = tm
        if tm.has_failure_notice and tm.failure_notice is not None:
            self.error_param_1 = struct.unpack("!I", tm.failure_notice.data[0:4])[0]
            self.error_param_2 = struct.unpack("!I", tm.failure_notice.data[4:8])[0]


PusVerifQueue = deque[Service1Tm]
