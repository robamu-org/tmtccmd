from abc import abstractmethod
from typing import Optional

from spacepackets.ecss.tm import PusTelemetry, PusVersion
from spacepackets.ccsds.time import CdsShortTimestamp


class PusTmInterface:

    @abstractmethod
    def pack(self) -> bytearray:
        return bytearray()

    @abstractmethod
    def get_tm_data(self) -> bytearray:
        return bytearray()

    @abstractmethod
    def is_valid(self) -> bool:
        return False

    @abstractmethod
    def get_ssc(self) -> int:
        return 0

    @abstractmethod
    def get_apid(self) -> int:
        return 0

    @abstractmethod
    def get_service(self) -> int:
        return -1

    @abstractmethod
    def get_subservice(self) -> int:
        return -1


class PusTmInfoInterface:
    @abstractmethod
    def get_print_info(self) -> str:
        return ''

    @abstractmethod
    def get_custom_printout(self) -> str:
        return ''

    @abstractmethod
    def get_source_data_string(self) -> str:
        return ''

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

    def get_tm_data(self) -> bytearray:
        return self.pus_tm.get_tm_data()

    def get_ssc(self) -> int:
        return self.pus_tm.get_ssc()

    def is_valid(self):
        return self.pus_tm.is_valid()

    def get_apid(self) -> int:
        return self.pus_tm.get_apid()

    def get_service(self) -> int:
        return self.pus_tm.get_service()

    def get_subservice(self) -> int:
        return self.pus_tm.get_subservice()


class PusTmInfoBase(PusTmInfoInterface):
    def __init__(self, pus_tm: PusTelemetry):
        self.pus_tm = pus_tm
        self._custom_printout = ''
        self._print_info = ''

    def get_print_info(self) -> str:
        return self._print_info

    def get_custom_printout(self) -> str:
        return self._custom_printout

    def set_custom_printout(self, custom_string: str):
        self._custom_printout = custom_string

    def get_source_data_string(self) -> str:
        return self.pus_tm.get_source_data_string()

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
        content_list.append(f'{self.pus_tm.get_service()}')
        content_list.append(f'{self.pus_tm.get_subservice()}')
        content_list.append(f'{self.pus_tm.secondary_packet_header.message_counter}')
        content_list.append(f'{self.pus_tm.secondary_packet_header.time.return_unix_seconds()}')
        content_list.append(f'{self.pus_tm.secondary_packet_header.time.return_time_string()}')
        content_list.append(f'0x{self.pus_tm.space_packet_header.apid:02x}')
        content_list.append(f'{self.pus_tm.space_packet_header.ssc}')
        if self.pus_tm.is_valid():
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
