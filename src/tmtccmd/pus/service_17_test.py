from __future__ import annotations
import enum
import sys

from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry
from spacepackets.ecss.service_17_test import Service17TM
from spacepackets.ecss.definitions import PusServices
from spacepackets.ecss.conf import get_default_tc_apid

from tmtccmd.config.definitions import QueueCommands
from tmtccmd.tc.definitions import PusTelecommand, TcQueueT
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase


class Srv17Subservices(enum.IntEnum):
    PING_CMD = (1,)
    PING_REPLY = (2,)
    GEN_EVENT = 128


class Service17TMExtended(PusTmBase, PusTmInfoBase, Service17TM):
    def __init__(
        self,
        subservice: int,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        Service17TM.__init__(
            self,
            subservice=subservice,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=self.pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=self.pus_tm)
        if self.subservice == Srv17Subservices.PING_REPLY:
            self.set_packet_info("Ping Reply")

    @classmethod
    def __empty(cls) -> Service17TMExtended:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service17TMExtended:
        service_17_tm = cls.__empty()
        service_17_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        return service_17_tm


def pack_service_17_ping_command(ssc: int, apid: int = -1) -> PusTelecommand:
    """Generate a simple ping PUS telecommand packet"""
    if apid == -1:
        apid = get_default_tc_apid()
    return PusTelecommand(
        service=17, subservice=Srv17Subservices.PING_CMD, ssc=ssc, apid=apid
    )


def pack_generic_service17_test(
    init_ssc: int, tc_queue: TcQueueT, apid: int = -1
) -> int:
    if apid == -1:
        apid = get_default_tc_apid()
    new_ssc = init_ssc
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17"))
    # ping test
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Ping Test"))
    tc_queue.appendleft(pack_service_17_ping_command(ssc=new_ssc).pack_command_tuple())
    new_ssc += 1
    # enable event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Enable Event"))
    command = PusTelecommand(service=5, subservice=5, ssc=new_ssc, apid=apid)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # test event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Trigger event"))
    command = PusTelecommand(
        service=17, subservice=Srv17Subservices.GEN_EVENT, ssc=new_ssc, apid=apid
    )
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    # invalid subservice
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 17: Invalid subservice"))
    command = PusTelecommand(service=17, subservice=243, ssc=new_ssc, apid=apid)
    tc_queue.appendleft(command.pack_command_tuple())
    new_ssc += 1
    return new_ssc
