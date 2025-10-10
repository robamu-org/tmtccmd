"""Contains classes and functions to handle PUS Service 8 telemetry."""

from __future__ import annotations

import struct

from spacepackets.ecss.tm import PusTelemetry

from tmtccmd.pus.s8_fsfw_action_defs import CustomSubservice
from tmtccmd.util.obj_id import ComponentIdU32


class Service8FsfwDataReply:
    """FSFW Action service data reply telemetry parser.

    This class can be used to parse the FSFW action data replies with the
    :py:class:`tmtccmd.pus.s8_fsfw_action_defs.CustomSubservice.TM_DATA_REPLY` subservice.
    It parses the object ID, the action ID and the reply data.

    Raises
    --------

    ValueError
        Subservice is not correct or the TM source data length is smaller than 8, which is the
        minimum required size to unpack object ID and action ID.
    """

    def __init__(self, pus_tm: PusTelemetry) -> None:
        if pus_tm.subservice != CustomSubservice.TM_DATA_REPLY:
            raise ValueError(
                f"invalid subservice {pus_tm.subservice}, expected {CustomSubservice.TM_DATA_REPLY}"
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
        #: Action ID.
        self.action_id: int = struct.unpack("!I", pus_tm.source_data[4:8])[0]
        #: Reply Data.
        self.reply_data: bytes = pus_tm.source_data[8:]
