"""Contains classes and functions to handle PUS Service 8 telemetry."""

from __future__ import annotations
import struct
from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.util.obj_id import ComponentIdU32
from tmtccmd.pus.s8_fsfw_action_defs import CustomSubservice


class Service8FsfwDataReply:
    def __init__(self, pus_tm: PusTelemetry) -> None:
        if pus_tm.subservice != CustomSubservice.TM_DATA_REPLY:
            raise ValueError(
                f"invalid subservice {pus_tm.subservice}, expected {CustomSubservice.TM_DATA_REPLY}"
            )
        self.pus_tm = pus_tm
        self.object_id = ComponentIdU32(struct.unpack("!i", pus_tm.source_data[0:4])[0])
        self.action_id = struct.unpack("!I", pus_tm.source_data[4:8])[0]
        self.reply_data = pus_tm.source_data[8:]
