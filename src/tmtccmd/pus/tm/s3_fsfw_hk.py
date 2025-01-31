# -*- coding: utf-8 -*-
"""PUS Service 3 components. FSFW specific support."""

from __future__ import annotations
import struct

from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.pus.s3_fsfw_hk import Subservice
from tmtccmd.util.obj_id import ComponentIdU32


class Service3FsfwHkPacket:
    def __init__(self, pus_tm: PusTelemetry) -> None:
        if (
            pus_tm.subservice != Subservice.TM_HK_REPORT
            and pus_tm.subservice != Subservice.TM_DIAGNOSTICS_REPORT
        ):
            raise ValueError(
                f"invalid subservice {pus_tm.subservice}, expected {Subservice.TM_HK_REPORT} or "
                f"{Subservice.TM_DIAGNOSTICS_REPORT}"
            )
        self.pus_tm = pus_tm
        self.object_id = ComponentIdU32(struct.unpack("!i", pus_tm.source_data[0:4])[0])
        self.set_id = struct.unpack("!I", pus_tm.source_data[4:8])[0]
        self.hk_data = pus_tm.source_data[8:]
