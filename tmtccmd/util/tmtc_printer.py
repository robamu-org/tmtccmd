"""Contains classes and functions that perform all printing functionalities.
"""
import logging
import enum
from typing import List, Optional

from spacepackets.util import get_printable_data_string, PrintFormats

from tmtccmd.tm.pus_8_fsfw_funccmd import Service8FsfwTm
from tmtccmd.tm.base import PusTmInfoInterface, PusTmInterface
from tmtccmd.util.obj_id import ObjectIdU32, ObjectIdBase
from tmtccmd.tm.pus_3_hk_base import HkContentType
from tmtccmd.logging import get_console_logger, get_current_time_string

LOGGER = get_console_logger()


class DisplayMode(enum.Enum):
    """List of display modes"""

    SHORT = enum.auto
    LONG = enum.auto


class FsfwTmTcPrinter:
    """This class handles printing to the command line and to files"""

    def __init__(
        self,
        file_logger: Optional[logging.Logger],
        display_mode: DisplayMode = DisplayMode.LONG,
    ):
        """
        :param display_mode:
        """
        self.display_mode = display_mode
        self.file_logger = file_logger

    @staticmethod
    def generic_short_string(packet_if: PusTmInterface) -> str:
        return f"Got TM[{packet_if.service}, {packet_if.subservice}]"

    def handle_long_tm_print(
        self, packet_if: PusTmInterface, info_if: PusTmInfoInterface
    ):
        """Main function to print the most important information inside the telemetry
        :param packet_if: Core packet interface
        :param info_if: Information interface
        :return:
        """
        base_string = "Got TM: " + info_if.get_print_info()
        LOGGER.info(base_string)
        if self.file_logger is not None:
            self.file_logger.info(f"{get_current_time_string(True)}: {base_string}")
        try:
            self.__handle_column_header_print(info_if=info_if)
            self.__handle_tm_content_print(info_if=info_if)
            self.__handle_additional_printout(info_if=info_if)
        except TypeError:
            LOGGER.exception(
                f"Type Error when trying to print TM Packet "
                f"[{packet_if.service}, {packet_if.subservice}]"
            )

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

    def generic_hk_tm_print(
        self,
        content_type: HkContentType,
        object_id: ObjectIdU32,
        set_id: int,
        hk_data: bytes,
    ):
        """This function pretty prints HK packets with a given header and content list
        :param content_type: Type of content for HK packet
        :param object_id: Object ID of the HK source
        :param set_id: Unique set ID for the HK packet
        :param hk_data: User defined HK data
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
            f"{print_prefix} from Object ID {object_id.name} ({object_id.as_hex_string}) with "
            f"Set ID {set_id} and {len(hk_data)} bytes of HK data"
        )
        LOGGER.info(generic_info)
        if self.file_logger is not None:
            self.file_logger.info(f"{get_current_time_string(True)}: {generic_info}")

    def print_validity_buffer(self, validity_buffer: bytes, num_vars: int):
        """
        :param validity_buffer: Validity buffer in bytes format
        :param num_vars: Number of variables
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

    @staticmethod
    def generic_action_packet_tm_print(
        packet: Service8FsfwTm, obj_id: ObjectIdBase
    ) -> str:
        print_string = (
            f"Service 8 data reply from {obj_id} with action ID {packet.action_id} "
            f"and data size {len(packet.tm_data)}"
        )
        return print_string

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

    @staticmethod
    def bit_extractor(byte: int, position: int):
        """

        :param byte:
        :param position:
        :return:
        """
        shift_number = position + (6 - 2 * (position - 1))
        return (byte >> shift_number) & 1

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
