# -*- coding: utf-8 -*-
"""Contains classes and functions to deserialize PUS Service 5 Telemetry"""

from __future__ import annotations

import dataclasses
import struct

from spacepackets import SpacePacketHeader
from spacepackets.ccsds.spacepacket import PacketId, PacketSeqCtrl
from spacepackets.ecss.defs import PusService
from spacepackets.ecss.pus_5_event import Subservice
from spacepackets.ecss.tm import CdsShortTimestamp, AbstractPusTm, MiscParams, PusTelemetry, PusTm
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
        return bytes(raw)

    @classmethod
    def empty(cls) -> EventDefinition:
        return cls(0, bytes([0, 0, 0, 0]), 0, 0)

    @classmethod
    def from_bytes(cls, data: bytes) -> EventDefinition:
        if len(data) < 14:
            raise ValueError("full FSFW event definition must be at least 14 bytes wide")
        event_id = struct.unpack("!H", data[0:2])[0]
        object_id = bytes(data[2:6])
        param1 = struct.unpack("!I", data[6:10])[0]
        param2 = struct.unpack("!I", data[10:14])[0]
        return cls(event_id, object_id, param1, param2)


class Service5Tm(AbstractPusTm):
    def __init__(
        self,
        apid: int,
        subservice: Subservice,
        event: EventDefinition,
        timestamp: bytes,
        ssc: int = 0,
        destination_id: int = 0,
        misc_params: MiscParams | None = None
    ):
        """Create a FSFW tailored Event Service 5 telemetry instance.
        Use the unpack function to create an instance from a raw bytestream instead.
        :raises ValueError: Invalid input arguments
        """
        self.pus_tm = PusTm(
            service=PusService.S5_EVENT,
            subservice=subservice,
            timestamp=timestamp,
            seq_count=ssc,
            source_data=event.pack(),
            apid=apid,
            destination_id=destination_id,
            misc_params=misc_params,
        )

    @property
    def sp_header(self) -> SpacePacketHeader:
        return self.pus_tm.space_packet_header

    @property
    def timestamp(self) -> bytes:
        return self.pus_tm.timestamp

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice

    @property
    def ccsds_version(self) -> int:
        return self.pus_tm.ccsds_version

    @property
    def packet_id(self) -> PacketId:
        return self.pus_tm.packet_id

    @property
    def packet_seq_control(self) -> PacketSeqCtrl:
        return self.pus_tm.packet_seq_control

    @property
    def source_data(self) -> bytes:
        return self.pus_tm.source_data

    @classmethod
    def __empty(cls) -> Service5Tm:
        return cls(
            apid=0x0,
            subservice=Subservice.TM_INFO_EVENT,
            event=EventDefinition.empty(),
            timestamp=CdsShortTimestamp.empty().pack(),
        )

    @classmethod
    def from_tm(cls, pus_tm: PusTelemetry) -> Service5Tm:
        instance = cls.__empty()
        instance.pus_tm = pus_tm
        return instance

    @classmethod
    def unpack(cls, data: bytes | bytearray, timestamp_len: int) -> Service5Tm:
        instance = cls.__empty()
        instance.pus_tm = PusTelemetry.unpack(data=data, timestamp_len=timestamp_len)
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
        raise ValueError(f"invalid severity for subservice {self.subservice}")

    @property
    def event_definition(self) -> EventDefinition:
        return EventDefinition.from_bytes(self.pus_tm.source_data)

    def __eq__(self, other: object):
        if not isinstance(other, Service5Tm):
            return False
        return self.pus_tm == other.pus_tm
