# -*- coding: utf-8 -*-
"""
Program: tmtcc_tm_service1.py
Date: 30.12.2019
Description: Deserialize Pus Verification TM
Author: R. Mueller
"""
import struct
from typing import Deque

from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.ecss.tm_creator import PusTelemetryCreator
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class Service1TM(PusTelemetry):
    """
    Service 1 TM class representation. Can be used to deserialize raw service 1 packets.
    """
    def __init__(self, byte_array: bytearray):
        super().__init__(byte_array)
        self.has_tc_error_code = False
        self.is_step_reply = False
        # Failure Reports with error code
        self.err_code = 0
        self.step_number = 0
        self.error_param1 = 0
        self.error_param2 = 0
        self.tc_packet_id = 0
        self.tc_ssc = 0
        if len(self._tm_data) < 4:
            LOGGER.warning("Service1TM: TM data less than 4 bytes!")
        self.tc_packet_id = self._tm_data[0] << 8 | self._tm_data[1]
        self.tc_ssc = ((self._tm_data[2] & 0x3F) << 8) | self._tm_data[3]
        if self.get_subservice() % 2 == 0:
            self.__handle_failure_verification()
        else:
            self.__handle_success_verification()

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
        if self.get_subservice() == 2:
            self.append_packet_info(" : Acceptance failure")
        elif self.get_subservice() == 4:
            self.append_packet_info(" : Start failure")
        elif self.get_subservice() == 6:
            self.is_step_reply = True
            self.append_packet_info(" : Step Failure")
            self.step_number = struct.unpack('>B', self._tm_data[4:5])[0]
            self.err_code = struct.unpack('>H', self._tm_data[5:7])[0]
            self.error_param1 = struct.unpack('>I', self._tm_data[7:11])[0]
            self.error_param2 = struct.unpack('>I', self._tm_data[11:15])[0]
        elif self.get_subservice() == 8:
            self.err_code = struct.unpack('>H', self._tm_data[4:6])[0]
            self.error_param1 = struct.unpack('>I', self._tm_data[6:10])[0]
            self.error_param2 = struct.unpack('>I', self._tm_data[10:14])[0]
        else:
            LOGGER.error("Service1TM: Invalid subservice")

    def __handle_success_verification(self):
        self.specify_packet_info("Success Verification")
        if self.get_subservice() == 1:
            self.append_packet_info(" : Acceptance success")
        elif self.get_subservice() == 3:
            self.append_packet_info(" : Start success")
        elif self.get_subservice() == 5:
            self.is_step_reply = True
            self.append_packet_info(" : Step Success")
            self.step_number = struct.unpack('>B', self._tm_data[4:5])[0]
        elif self.get_subservice() == 7:
            self.append_packet_info(" : Completion success")
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


class Service1TmPacked(PusTelemetryCreator):
    """
    Class representation for Service 1 TM creation.
    """
    def __init__(self, subservice: int, ssc: int = 0, tc_packet_id: int = 0, tc_ssc: int = 0):
        source_data = bytearray()
        source_data.append((tc_packet_id & 0xFF00) >> 8)
        source_data.append(tc_packet_id & 0xFF)
        tc_psc = (tc_ssc & 0x3FFF) | (0b11 << 16)
        source_data.append((tc_psc & 0xFF00) >> 8)
        source_data.append(tc_psc & 0xFF)
        super().__init__(service=1, subservice=subservice, ssc=ssc, source_data=source_data)

    def pack(self) -> bytearray:
        return super().pack()


PusVerifQueue = Deque[Service1TM]
