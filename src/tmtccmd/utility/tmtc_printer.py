"""Contains classes and functions that perform all printing functionalities.
"""
import logging
import os
import enum
from datetime import datetime
from typing import cast, List, Optional

from spacepackets.ecss.tc import PusTelecommand
from spacepackets.util import get_printable_data_string, PrintFormats

from tmtccmd.tm.service_8_fsfw_functional_cmd import Service8FsfwTm
from tmtccmd.tm.service_5_event import Service5Tm
from tmtccmd.pus.service_1_verification import Service1TMExtended
from spacepackets.ecss.definitions import PusServices
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface
from tmtccmd.pus import ObjectId
from tmtccmd.pus.service_8_func_cmd import Srv8Subservices
from tmtccmd.tm.definitions import PusIFQueueT
from tmtccmd.tm.service_3_base import Service3Base, HkContentType
from tmtccmd.logging import get_console_logger

LOGGER = get_console_logger()


class DisplayMode(enum.Enum):
    """List of display modes"""

    SHORT = enum.auto()
    LONG = enum.auto()


class FsfwTmTcPrinter:
    """This class handles printing to the command line and to files"""

    def __init__(
        self,
        file_logger: Optional[logging.Logger],
        display_mode: DisplayMode = DisplayMode.LONG,
    ):
        """
        :param display_mode:
        :param do_print_to_file: if true, print to file
        :param print_tc: if true, print TCs
        """
        self.display_mode = display_mode
        self.file_logger = file_logger

    @staticmethod
    def generic_short_string(packet_if: PusTmInterface) -> str:
        return f"Received TM[{packet_if.service}, {packet_if.subservice}]"

    def handle_long_tm_print(
        self, packet_if: PusTmInterface, info_if: PusTmInfoInterface
    ):
        """Main function to print the most important information inside the telemetry
        :param packet_if: Core packet interface
        :param info_if: Information interface
        :return:
        """
        base_string = "Received Telemetry: " + info_if.get_print_info()
        LOGGER.info(base_string)
        if self.file_logger is not None:
            self.file_logger.info(f"{self.get_time_string(True)}: {base_string}")
        try:
            self.__handle_column_header_print(info_if=info_if)
            self.__handle_tm_content_print(info_if=info_if)
            self.__handle_additional_printout(info_if=info_if)
        except TypeError as error:
            LOGGER.exception(
                f"Type Error when trying to print TM Packet "
                f"[{packet_if.service}, {packet_if.subservice}]"
            )

    def get_time_string(self, ms_prec: bool) -> str:
        base_fmt = "%Y-%m-%d %H:%M:%S"
        if ms_prec:
            base_fmt += ".%f"
            return datetime.now().strftime(base_fmt)[:-3]
        return datetime.now().strftime(base_fmt)

    def __handle_column_header_print(self, info_if: PusTmInfoInterface):
        header_list = []
        info_if.append_telemetry_column_headers(header_list=header_list)
        print(header_list)
        if self.file_logger is not None:
            self.file_logger.info(header_list)

    def __handle_tm_content_print(self, info_if: PusTmInfoInterface):
        """
        :param info_if: Information interface
        :return:
        """
        content_list = []
        info_if.append_telemetry_content(content_list=content_list)
        print(content_list)
        if self.file_logger is not None:
            self.file_logger.info(content_list)

    def __handle_additional_printout(self, info_if: PusTmInfoInterface):
        additional_printout = info_if.get_custom_printout()
        if additional_printout is not None and additional_printout != "":
            LOGGER.info(additional_printout)
            if self.file_logger is not None:
                print(additional_printout)

    def generic_hk_print(
        self,
        content_type: HkContentType,
        object_id: ObjectId,
        set_id: int,
        hk_data: bytes,
    ):
        """This function pretty prints HK packets with a given header and content list
        :param content_type: Type of content for HK packet
        :return:
        """
        if content_type == HkContentType.HK:
            print_prefix = "Housekeeping data"
        elif content_type == HkContentType.DEFINITIONS:
            print_prefix = "Housekeeping definitions"
        else:
            print_prefix = "Unknown housekeeping data"
        if object_id.name == "":
            object_id.name = "Unknown Name"
        generic_info = (
            f"{print_prefix} from Object ID {object_id.name} ({object_id.as_string}) with "
            f"Set ID {set_id} and {len(hk_data)} bytes of HK data"
        )
        LOGGER.info(generic_info)
        if self.file_logger is not None:
            self.file_logger.info(f"{self.get_time_string(True)}: {generic_info}")

    def print_validity_buffer(self, validity_buffer: bytes, num_vars: int):
        """
        :param validity_buffer: Validity buffer in bytes format
        :return:
        """
        valid_list = []
        counter = 0
        for index, byte in enumerate(validity_buffer):
            for bit in range(1, 9):
                if self.bit_extractor(byte, bit) == 1:
                    valid_list.append(True)
                else:
                    valid_list.append(False)
                counter += 1
                if counter == num_vars:
                    break
        validity_lists = list(self.chunks(n=16, lst=valid_list))
        for valid_list in validity_lists:
            printout = "Valid: ["
            for idx, valid in enumerate(valid_list):
                if valid:
                    printout += "Y"
                else:
                    printout += "N"
                if idx < len(valid_list) - 1:
                    printout += ","
                else:
                    printout += "]"
            print(printout)
            if self.file_logger is not None:
                self.file_logger.info(printout)

    def print_telemetry_queue(self, tm_queue: PusIFQueueT):
        """Print the telemetry queue which should contain lists of TM class instances."""
        for tm_list in tm_queue:
            for tm_packet in tm_list:
                self.print_telemetry(packet_if=tm_packet, info_if=tm_packet)

    def print_telemetry(
        self,
        packet_if: PusTmInterface,
        info_if: PusTmInfoInterface,
        print_raw_tm: bool = False,
    ):
        """This function handles printing telemetry
        :param packet_if:       Core interface to work with PUS packets
        :param info_if:         Core interface to get custom data from PUS packets
        :param print_raw_tm:    Specify whether the TM packet is printed in a raw way.
        :return:
        """
        if not isinstance(packet_if, PusTmInterface) or not isinstance(
            info_if, PusTmInfoInterface
        ):
            LOGGER.warning("Passed packet does not implement necessary interfaces!")
            return
        # TODO: Maybe remove this function altogether?
        # if self.display_mode == DisplayMode.SHORT:
        #     self.__handle_short_print(packet_if)
        # else:
        #    self.__handle_long_tm_print(packet_if=packet_if, info_if=info_if)
        self.__handle_wiretapping_packet(packet_if=packet_if, info_if=info_if)

        if (
            packet_if.service == PusServices.SERVICE_8_FUNC_CMD
            and packet_if.subservice == Srv8Subservices.DATA_REPLY
        ):
            self.handle_service_8_packet(packet_if=packet_if)

        if print_raw_tm:
            tm_data_string = get_printable_data_string(
                print_format=PrintFormats.HEX, data=packet_if.pack()
            )

    def handle_service_8_packet(self, packet_if: PusTmInterface):
        from tmtccmd.config.hook import get_global_hook_obj

        if packet_if.service != PusServices.SERVICE_8_FUNC_CMD:
            LOGGER.warning("This packet is not a service 8 packet!")
            return
        if packet_if.subservice != Srv8Subservices.DATA_REPLY:
            LOGGER.warning(
                f"This packet is not data reply packet with "
                f"subservice {Srv8Subservices.DATA_REPLY}!"
            )
            return
        hook_obj = get_global_hook_obj()
        if hook_obj is None:
            LOGGER.warning("Hook object not set")
            return
        srv8_packet = cast(Service8FsfwTm, packet_if)
        if srv8_packet is None:
            LOGGER.warning("Service 8 object is not instance of Service8TM")
            return
        obj_id = srv8_packet.source_object_id_as_bytes
        action_id = srv8_packet.action_id
        reply = hook_obj.handle_service_8_telemetry(
            object_id=obj_id, action_id=action_id, custom_data=srv8_packet.custom_data
        )
        obj_id_dict = hook_obj.get_object_ids()
        rep_str = obj_id_dict.get(bytes(obj_id))
        if rep_str is None:
            rep_str = "unknown object"
        print_string = f"Service 8 data reply from {rep_str} with action ID {action_id}"
        self.__print_buffer = print_string
        LOGGER.info(self.__print_buffer)
        self.add_print_buffer_to_file_buffer()
        self.__print_buffer = reply.header_list
        LOGGER.info(self.__print_buffer)
        self.add_print_buffer_to_file_buffer()
        self.__print_buffer = reply.content_list
        LOGGER.info(self.__print_buffer)
        self.add_print_buffer_to_file_buffer()

    def __handle_wiretapping_packet(
        self, packet_if: PusTmInterface, info_if: PusTmInfoInterface
    ):
        """
        :param packet_if: Core packet interface
        :param info_if: Information interface
        :return:
        """
        if packet_if.service == 2 and (
            packet_if.subservice == 131 or packet_if.subservice == 130
        ):
            self.__print_buffer = (
                f"Wiretapping Packet or Raw Reply from TM [{packet_if.service},"
                f"{packet_if.subservice}]: "
            )
            self.__print_buffer = self.__print_buffer + info_if.get_source_data_string()
            LOGGER.info(self.__print_buffer)
            self.add_print_buffer_to_file_buffer()

    @staticmethod
    def bit_extractor(byte: int, position: int):
        """

        :param byte:
        :param position:
        :return:
        """
        shift_number = position + (6 - 2 * (position - 1))
        return (byte >> shift_number) & 1

    def print_telecommand(
        self, tc_packet_obj: PusTelecommand, tc_packet_raw: bytearray = bytes()
    ):
        """
        This function handles the printing of Telecommands. It assumed the packets are sent
        shortly before or after.
        :param tc_packet_obj:
        :param tc_packet_raw:
        :return:
        """
        if tc_packet_obj is None:
            LOGGER.error("TMTC Printer: Invalid telecommand")
            return
        if self.display_mode == DisplayMode.SHORT:
            self._handle_short_tc_print(tc_packet_obj=tc_packet_obj)
        else:
            self._handle_long_tc_print(tc_packet_obj=tc_packet_obj)

    def _handle_short_tc_print(self, tc_packet_obj: PusTelecommand):
        """
        Brief TC print
        :param tc_packet_obj:
        :return:
        """
        # TODO: Refactor this
        """
        self.__print_buffer = (
            f"Sent TC[{tc_packet_obj.service}, {tc_packet_obj.subservice}] with SSC "
            f"{tc_packet_obj.ssc}"
        )
        LOGGER.info(self.__print_buffer)
        """



    def _handle_long_tc_print(self, tc_packet_obj: PusTelecommand):
        """
        Long TC print
        :param tc_packet_obj:
        :return:
        """
        # TODO: Refactor this
        data_print = get_printable_data_string(
            print_format=PrintFormats.HEX, data=tc_packet_obj.app_data
        )
        try:
            """
            self.__print_buffer = (
                f"Telecommand TC[{tc_packet_obj.service}, {tc_packet_obj.subservice}] "
                f"with SSC {tc_packet_obj.ssc} sent with data "
                f"{data_print}"
            )
            LOGGER.info(self.__print_buffer)
            """
        except TypeError as error:
            LOGGER.error("TMTC Printer: Type Error! Traceback: %s", error)

    @staticmethod
    def print_data(data: bytes):
        """
        :param data: Data to print
        :return: None
        """
        string = get_printable_data_string(print_format=PrintFormats.HEX, data=data)
        LOGGER.info(string)

    @staticmethod
    def chunks(lst: List, n) -> List[List]:
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]
