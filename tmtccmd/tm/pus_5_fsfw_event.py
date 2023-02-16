# -*- coding: utf-8 -*-
"""Contains classes and functions to deserialize PUS Service 5 Telemetry
"""
from __future__ import annotations

import dataclasses
import struct
from typing import Optional

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.time import CcsdsTimeProvider
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.pus_5_event import Subservice
from spacepackets.ecss.tm import CdsShortTimestamp, AbstractPusTm, PusTelemetry
from tmtccmd.pus.s5_fsfw_event_defs import Severity


@dataclasses.dataclass
class EventDefinition:
    event_id: int
    reporter_id: bytes
    param1: int
    param2: int

    def pack(self) -> bytes:
        raw = bytearray(struct.pack("!H", self.event_id))
        if len(self.reporter_id) < 4:
            raise ValueError("reporter ID must be at least 4 bytes wide")
        raw.extend(self.reporter_id)
        raw.extend(struct.pack("!I", self.param1))
        raw.extend(struct.pack("!I", self.param2))
        return raw

    @classmethod
    def empty(cls) -> EventDefinition:
        return cls(0, bytes([0, 0, 0, 0]), 0, 0)

    @classmethod
    def from_bytes(cls, data: bytes) -> EventDefinition:
        if len(data) < 14:
            raise ValueError(
                "full FSFW event definition must be at least 14 bytes wide"
            )
        event_id = struct.unpack("!H", data[0:2])[0]
        object_id = bytes(data[2:6])
        param1 = struct.unpack("!I", data[6:10])[0]
        param2 = struct.unpack("!I", data[10:14])[0]
        return cls(event_id, object_id, param1, param2)


class Service5Tm(AbstractPusTm):
    def __init__(
        self,
        subservice: Subservice,
        event: EventDefinition,
        time_provider: Optional[CdsShortTimestamp],
        ssc: int = 0,
        apid: int = -1,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        """Create a FSFW tailored Event Service 5 telemetry instance.
        Use the unpack function to create an instance from a raw bytestream instead.
        :raises ValueError: Invalid input arguments
        """
        self.pus_tm = PusTelemetry(
            service=PusService.S5_EVENT,
            subservice=subservice,
            time_provider=time_provider,
            seq_count=ssc,
            source_data=event.pack(),
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def time_provider(self) -> Optional[CcsdsTimeProvider]:
        return self.pus_tm.time_provider

    def pack(self) -> bytes:
        return self.pus_tm.pack()

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    @classmethod
    def __empty(cls) -> Service5Tm:
        return cls(
            subservice=Subservice.TM_INFO_EVENT,
            event=EventDefinition.empty(),
            time_provider=CdsShortTimestamp.empty(),
        )

    @classmethod
    def from_tm(cls, pus_tm: PusTelemetry) -> Service5Tm:
        instance = cls.__empty()
        instance.pus_tm = pus_tm
        return instance

    @classmethod
    def unpack(
        cls, data: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> Service5Tm:
        instance = cls.__empty()
        instance.pus_tm = PusTelemetry.unpack(data=data, time_reader=time_reader)
        return instance

    @property
    def severity(self) -> Severity:
        if self.subservice == Subservice.TM_INFO_EVENT:
            return Severity.INFO
        elif self.subservice == Subservice.TM_LOW_SEVERITY_EVENT:
            return Severity.LOW
        elif self.subservice == Subservice.TM_MEDIUM_SEVERITY_EVENT:
            return Severity.MEDIUM
        elif self.subservice == Subservice.TM_HIGH_SEVERITY_EVENT:
            return Severity.HIGH

    @property
    def event_definition(self) -> EventDefinition:
        return EventDefinition.from_bytes(self.pus_tm.source_data)

    def __eq__(self, other: Service5Tm):
        return self.pus_tm == other.pus_tm
