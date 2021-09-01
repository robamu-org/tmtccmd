from abc import abstractmethod
from typing import Optional


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
