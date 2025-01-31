# -*- coding: utf-8 -*-
"""PUS Service 3 components. FSFW specific support."""

from __future__ import annotations
import struct

from spacepackets.ecss.tm import PusTelemetry
from tmtccmd.pus.s3_fsfw_hk import Subservice
from tmtccmd.util.obj_id import ComponentIdU32


class Service3FsfwHkPacket:
    """Housekeeping service HK telemetry parser.

    This class can be used to parse the FSFW HK packets for HK packets with the
    :py:class:`spacepackets.ecss.pus_3_hk.Subservice` `TM_HK_REPORT` (25) and `TM_DIAGNOSTICS_REPORT`
    (26) subservice.
    It parses the object ID, set ID fields and the HK data.

    Raises
    --------

    ValueError
        Subservice is not correct or the TM source data length is smaller than 8, which is the
        minimum required size to unpack object ID and set ID.
    """

    def __init__(self, pus_tm: PusTelemetry) -> None:
        if (
            pus_tm.subservice != Subservice.TM_HK_REPORT
            and pus_tm.subservice != Subservice.TM_DIAGNOSTICS_REPORT
        ):
            raise ValueError(
                f"invalid subservice {pus_tm.subservice}, expected {Subservice.TM_HK_REPORT} or "
                f"{Subservice.TM_DIAGNOSTICS_REPORT}"
            )

        if len(pus_tm.source_data) < 8:
            raise ValueError(
                f"not enough data available, expected at least 8 bytes, found {len(pus_tm.source_data)}"
            )

        #: Corresponding PUS TM packet.
        self.pus_tm: PusTelemetry = pus_tm
        #: Object ID.
        self.object_id: ComponentIdU32 = ComponentIdU32(
            struct.unpack("!i", pus_tm.source_data[0:4])[0]
        )
        #: Housekeeping Set ID.
        self.set_id: int = struct.unpack("!I", pus_tm.source_data[4:8])[0]
        #: Housekeeping Data.
        self.hk_data: bytes = pus_tm.source_data[8:]
