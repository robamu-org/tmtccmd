# -*- coding: utf-8 -*-
"""Deserialize PUS Service 1 Verification TM
"""
from __future__ import annotations
from abc import abstractmethod
import struct
from typing import Deque

from tmtccmd.ecss.tm import PusTelemetry, PusVersion, PusTmInfoBase, PusTmBase
from tmtccmd.ccsds.time import CdsShortTimestamp
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class Service1TM(PusTmBase, PusTmInfoBase):
    """Service 1 TM class representation. Can be used to deserialize raw service 1 packets.
    """
    def __init__(
            self, subservice_id: int, time: CdsShortTimestamp = None,
            tc_packet_id: int = 0, tc_psc: int = 0, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, packet_version: int = 0b000,
            pus_version: PusVersion = PusVersion.UNKNOWN, pus_tm_version: int = 0b0001,
            ack: int = 0b1111, secondary_header_flag: bool = True, space_time_ref: int = 0b0000,
            destination_id: int = 0
    ):
        pus_tm = PusTelemetry(
            service_id=1,
            subservice_id=subservice_id,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            pus_tm_version=pus_tm_version,
            ack=ack,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id
        )
        PusTmBase.__init__(self, pus_tm=pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        self.has_tc_error_code = False
        self.is_step_reply = False
        # Failure Reports with error code
        self.err_code = 0
        self.step_number = 0
        self.error_param1 = 0
        self.error_param2 = 0
        self.tc_packet_id = tc_packet_id
        self.tc_psc = tc_psc
        self.tc_ssc = tc_psc & 0x3fff

    @classmethod
    def __empty(cls):
        return cls(
            subservice_id=0
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.UNKNOWN
    ) -> Service1TM:
        service_1_tm = cls.__empty()
        service_1_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        tm_data = service_1_tm.get_tm_data()
        if len(tm_data) < 4:
            LOGGER.warning("TM data less than 4 bytes!")
            raise ValueError
        service_1_tm.tc_packet_id = tm_data[0] << 8 | tm_data[1]
        service_1_tm.tc_psc = tm_data[2] << 8 | tm_data[3]
        service_1_tm.tc_ssc = service_1_tm.tc_psc & 0x3fff
        if service_1_tm.get_subservice() % 2 == 0:
            service_1_tm.__handle_failure_verification()
        else:
            service_1_tm.__handle_success_verification()
        return service_1_tm

    @abstractmethod
    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(hex(self.tc_packet_id)))
        content_list.append(str(self.tc_ssc))
        if self.has_tc_error_code:
            if self.is_step_reply:
                content_list.append(str(self.step_number))
            content_list.append(str(hex(self.err_code)))
            content_list.append(str(hex(self.error_param1)) + ", " + str(self.error_param1))
            content_list.append(str(hex(self.error_param2)) + ", " + str(self.error_param2))
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

    def __handle_failure_verification(self):
        self.specify_packet_info("Failure Verficiation")
        self.has_tc_error_code = True
        tm_data = self.get_tm_data()
        if self.get_subservice() == 2:
            self.append_packet_info(" : Acceptance failure")
        elif self.get_subservice() == 4:
            self.append_packet_info(" : Start failure")
        elif self.get_subservice() == 6:
            self.is_step_reply = True
            self.append_packet_info(" : Step Failure")
            self.step_number = struct.unpack('>B', tm_data[4:5])[0]
            self.err_code = struct.unpack('>H', tm_data[5:7])[0]
            self.error_param1 = struct.unpack('>I', tm_data[7:11])[0]
            self.error_param2 = struct.unpack('>I', tm_data[11:15])[0]
        elif self.get_subservice() == 8:
            self.err_code = struct.unpack('>H', tm_data[4:6])[0]
            self.error_param1 = struct.unpack('>I', tm_data[6:10])[0]
            self.error_param2 = struct.unpack('>I', tm_data[10:14])[0]
        else:
            LOGGER.error("Service1TM: Invalid subservice")

    def __handle_success_verification(self):
        self.pus_tm.specify_packet_info("Success Verification")
        if self.get_subservice() == 1:
            self.pus_tm.append_packet_info(" : Acceptance success")
        elif self.get_subservice() == 3:
            self.pus_tm.append_packet_info(" : Start success")
        elif self.get_subservice() == 5:
            self.is_step_reply = True
            self.pus_tm.append_packet_info(" : Step Success")
            self.step_number = struct.unpack('>B', self.get_tm_data()[4:5])[0]
        elif self.get_subservice() == 7:
            self.pus_tm.append_packet_info(" : Completion success")
        else:
            LOGGER.error("Service1TM: Invalid subservice")

    def get_tc_ssc(self):
        return self.tc_ssc

    def get_error_code(self):
        if self.has_tc_error_code:
            return self.err_code
        else:
            LOGGER.warning("Service1Tm: get_error_code: This is not a failure packet, returning 0")
            return 0

    def get_step_number(self):
        if self.is_step_reply:
            return self.step_number
        else:
            LOGGER.warning("Service1Tm: get_step_number: This is not a step reply, returning 0")
            return 0


PusVerifQueue = Deque[Service1TM]
