from abc import abstractmethod
from typing import Optional

from spacepackets.ecss.tm import PusTelemetry


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
    def return_source_data_string(self) -> str:
        return ''

    @abstractmethod
    def specify_packet_info(self, print_info: str):
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

    def get_print_info(self) -> str:
        return self.pus_tm.print_info

    def get_custom_printout(self) -> str:
        return self.pus_tm.get_custom_printout()

    def return_source_data_string(self) -> str:
        return self.pus_tm.return_source_data_string()

    def specify_packet_info(self, print_info: str):
        self.pus_tm.print_info = print_info

    def append_packet_info(self, info: str):
        self.pus_tm.print_info += info

    def append_telemetry_column_headers(self, header_list: list):
        self.pus_tm.append_telemetry_column_headers(header_list=header_list)

    def append_telemetry_content(self, content_list: list):
        self.pus_tm.append_telemetry_content(content_list=content_list)
