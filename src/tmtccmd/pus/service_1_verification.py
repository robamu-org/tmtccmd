# -*- coding: utf-8 -*-
"""Deserialize PUS Service 1 Verification TM
"""
from __future__ import annotations
from abc import abstractmethod
import struct
from typing import Deque

from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.tm import PusVersion, PusTelemetry
from spacepackets.ecss.service_1_verification import Service1TM

from tmtccmd.tm.base import PusTmInfoBase, PusTmBase
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class Service1TMExtended(PusTmBase, PusTmInfoBase, Service1TM):
    """Service 1 TM class representation. Can be used to deserialize raw service 1 packets."""

    def __init__(
        self,
        subservice: int,
        time: CdsShortTimestamp = None,
        tc_packet_id: int = 0,
        tc_psc: int = 0,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        Service1TM.__init__(
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

    @classmethod
    def __empty(cls) -> Service1TMExtended:
        return cls(subservice=0)

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service1TMExtended:
        """Parse a service 1 telemetry packet

        :param raw_telemetry:
        :param pus_version:
        :raises ValueError: Raw telemetry too short
        :return:
        """
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        tm_data = service_1_tm.tm_data
        if len(tm_data) < 4:
            LOGGER.warning("TM data less than 4 bytes!")
            raise ValueError
        service_1_tm.tc_packet_id = tm_data[0] << 8 | tm_data[1]
        service_1_tm.tc_psc = tm_data[2] << 8 | tm_data[3]
        service_1_tm.tc_ssc = service_1_tm.tc_psc & 0x3FFF
        if service_1_tm.subservice % 2 == 0:
            service_1_tm._handle_failure_verification()
        else:
            service_1_tm._handle_success_verification()
        return service_1_tm

    @abstractmethod
    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(hex(self.tc_packet_id)))
        content_list.append(str(self.tc_ssc))
        if self.has_tc_error_code:
            if self.is_step_reply:
                content_list.append(str(self.step_number))
            content_list.append(str(hex(self.error_code)))
            content_list.append(
                f"hex {self.error_param_1:04x} dec {self.error_param_1}"
            )
            content_list.append(
                f"hex {self.error_param_2:04x} dec {self.error_param_2}"
            )
        elif self.is_step_reply:
            content_list.append(str(self.step_number))

    @abstractmethod
    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("TC Packet ID")
        header_list.append("TC SSC")
        if self.has_tc_error_code:
            if self.is_step_reply:
                header_list.append("Step Number")
            header_list.append("Return Value")
            header_list.append("Error Param 1")
            header_list.append("Error Param 2")
        elif self.is_step_reply:
            header_list.append("Step Number")

    def _handle_failure_verification(self):
        """Handle parsing a verification failure packet, subservice ID 2, 4, 6 or 8"""
        super()._handle_failure_verification()
        self.set_packet_info("Failure Verficiation")
        subservice = self.pus_tm.subservice
        if subservice == 2:
            self.append_packet_info(" : Acceptance failure")
        elif subservice == 4:
            self.append_packet_info(" : Start failure")
        elif subservice == 6:
            self.append_packet_info(" : Step Failure")
        elif subservice == 8:
            self.append_packet_info(" : Completion Failure")

    def _handle_success_verification(self):
        super()._handle_success_verification()
        self.set_packet_info("Success Verification")
        if self.subservice == 1:
            self.append_packet_info(" : Acceptance success")
        elif self.subservice == 3:
            self.append_packet_info(" : Start success")
        elif self.subservice == 5:
            self.append_packet_info(" : Step Success")
        elif self.subservice == 7:
            self.append_packet_info(" : Completion success")


PusVerifQueue = Deque[Service1TM]
