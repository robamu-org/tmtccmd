from abc import abstractmethod, ABC
from typing import Optional

from spacepackets.ecss.tm import PusTelemetry, PusVersion
from spacepackets.ccsds.time import CdsShortTimestamp
from spacepackets.util import PrintFormats


class PusTmInterface:
    @abstractmethod
    def pack(self) -> bytearray:
        raise NotImplementedError

    @property
    @abstractmethod
    def tm_data(self) -> bytearray:
        raise NotImplementedError

    @property
    @abstractmethod
    def valid(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def ssc(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def apid(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def service(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def subservice(self) -> int:
        raise NotImplementedError


class PusTmInfoInterface:
    @abstractmethod
    def get_print_info(self) -> str:
        return ""

    @abstractmethod
    def get_custom_printout(self) -> str:
        return ""

    @abstractmethod
    def get_source_data_string(self) -> str:
        return ""

    @abstractmethod
    def set_packet_info(self, print_info: str):
        pass

    @abstractmethod
    def append_packet_info(self, info: str):
        pass

    @abstractmethod
    def append_telemetry_column_headers(self, header_list: list):
        pass

    @abstractmethod
    def append_telemetry_content(self, content_list: list):
        pass


class PusTmBase(PusTmInterface):
    def __init__(self, pus_tm: PusTelemetry):
        self.pus_tm = pus_tm

    def pack(self) -> bytearray:
        return self.pus_tm.pack()

    @property
    def tm_data(self) -> bytearray:
        return self.pus_tm.tm_data

    @property
    def ssc(self) -> int:
        return self.pus_tm.ssc

    @property
    def valid(self):
        return self.pus_tm.valid

    @property
    def apid(self) -> int:
        return self.pus_tm.apid

    @property
    def service(self) -> int:
        return self.pus_tm.service

    @property
    def subservice(self) -> int:
        return self.pus_tm.subservice


class PusTmInfoBase(PusTmInfoInterface):
    def __init__(self, pus_tm: PusTelemetry):
        self.pus_tm = pus_tm
        self._custom_printout = ""
        self._print_info = ""

    def get_print_info(self) -> str:
        return self._print_info

    def get_custom_printout(self) -> str:
        return self._custom_printout

    def set_custom_printout(self, custom_string: str):
        self._custom_printout = custom_string

    def get_source_data_string(
        self, print_format: PrintFormats = PrintFormats.HEX
    ) -> str:
        return self.pus_tm.get_source_data_string(print_format=print_format)

    def set_packet_info(self, print_info: str):
        self._print_info = print_info

    def append_packet_info(self, info: str):
        self._print_info += info

    def append_telemetry_content(self, content_list: list):
        """Default implementation adds the PUS header content to the list which can then be
        printed with a simple print() command. To add additional content, override this method.
        Any child class should call this function as well if header information is required.

        :param content_list: Header content will be appended to this list
        :return:
        """
        content_list.append(f"{self.pus_tm.service}")
        content_list.append(f"{self.pus_tm.subservice}")
        content_list.append(f"{self.pus_tm.secondary_packet_header.message_counter}")
        content_list.append(
            f"{self.pus_tm.secondary_packet_header.time.return_unix_seconds()}"
        )
        content_list.append(
            f"{self.pus_tm.secondary_packet_header.time.return_time_string()}"
        )
        content_list.append(f"0x{self.pus_tm.space_packet_header.apid:02x}")
        content_list.append(f"{self.pus_tm.space_packet_header.ssc}")
        if self.pus_tm.valid:
            content_list.append("Yes")
        else:
            content_list.append("No")

    def append_telemetry_column_headers(self, header_list: list):
        """Default implementation adds the PUS header content header (confusing, I know)
        to the list which can then be printed with a simple print() command.
        To add additional headers, override this method. Any child class should
        call this function as well if header information is required.

        :param header_list: Header content will be appended to this list
        :return:
        """
        header_list.append("Service")
        header_list.append("Subservice")
        header_list.append("MSG Counter")
        header_list.append("Time (Unix Seconds)")
        header_list.append("Time")
        header_list.append("APID")
        header_list.append("SSC")
        header_list.append("Packet valid")
