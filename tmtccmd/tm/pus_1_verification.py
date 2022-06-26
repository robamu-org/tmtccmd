from __future__ import annotations

import struct
from abc import abstractmethod
from typing import Deque

from spacepackets.ccsds.spacepacket import PacketSeqCtrl
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.ecss.tm import PusVersion, PusTelemetry
from spacepackets.ecss.pus_1_verification import Service1Tm, Subservices, RequestId

from tmtccmd.tm.base import PusTmInfoBase, PusTmBase
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class Service1TmExtended(PusTmBase, PusTmInfoBase, Service1Tm):
    """Service 1 TM class representation. Can be used to deserialize raw service 1 packets."""

    def __init__(
        self,
        subservice: int,
        tc_request_id: RequestId,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        Service1Tm.__init__(
            self,
            tc_request_id=tc_request_id,
            subservice=subservice,
            time=time,
            ssc=ssc,
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
    def __empty(cls) -> Service1TmExtended:
        return cls(subservice=0, tc_request_id=RequestId.empty())

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytes,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service1TmExtended:
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
        cls._unpack_raw_tm(service_1_tm)
        return service_1_tm

    @abstractmethod
    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(self.tc_req_id.tc_packet_id)
        content_list.append(self.tc_req_id.tc_psc)
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
        header_list.append("TC PSC")
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
        if subservice == Subservices.TM_ACCEPTANCE_FAILURE:
            self.append_packet_info(" : Acceptance failure")
        elif subservice == Subservices.TM_START_FAILURE:
            self.append_packet_info(" : Start failure")
        elif subservice == Subservices.TM_STEP_FAILURE:
            self.append_packet_info(" : Step Failure")
        elif subservice == Subservices.TM_COMPLETION_FAILURE:
            self.append_packet_info(" : Completion Failure")

    def _handle_success_verification(self):
        super()._handle_success_verification()
        self.set_packet_info("Success Verification")
        if self.subservice == Subservices.TM_ACCEPTANCE_SUCCESS:
            self.append_packet_info(" : Acceptance success")
        elif self.subservice == Subservices.TM_START_SUCCESS:
            self.append_packet_info(" : Start success")
        elif self.subservice == Subservices.TM_STEP_SUCCESS:
            self.append_packet_info(" : Step Success")
        elif self.subservice == Subservices.TM_COMPLETION_SUCCESS:
            self.append_packet_info(" : Completion success")


PusVerifQueue = Deque[Service1Tm]
