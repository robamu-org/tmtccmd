"""Base class for Service 200 mode commanding reply handling."""

from __future__ import annotations

import struct

from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.pus.s200_fsfw_mode import Subservice


class Service200FsfwReader:
    def __init__(self, tm: PusTelemetry) -> None:
        self.tm = tm
        if len(tm.source_data) < 4:
            raise ValueError("service 200 TM can not even hold object ID")
        self.object_id = tm.source_data[0:4]
        self.return_value = None
        if tm.subservice == Subservice.TM_CANT_REACH_MODE:
            self.return_value = struct.unpack("!H", tm.source_data[4:6])[0]
        self.mode = None
        self.submode = None
        if (
            tm.subservice == Subservice.TM_MODE_REPLY
            or tm.subservice == Subservice.TM_WRONG_MODE_REPLY
        ):
            self.mode = struct.unpack("!I", tm.source_data[4:8])[0]
            self.submode = tm.source_data[8]

    def contains_mode(self) -> bool:
        if self.mode is not None and self.submode is not None:
            return True
        return False

    def is_cant_reach_mode_reply(self) -> bool:
        return self.tm.subservice == Subservice.TM_CANT_REACH_MODE
