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


class PusTelemetryExtended(PusTelemetry):
    def __init__(
            self, service_id: int, subservice_id: int, time: CdsShortTimestamp = None, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, message_counter: int = 0,
            space_time_ref: int = 0b0000, destination_id: int = 0,
            packet_version: int = 0b000, pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
            pus_tm_version: int = 0b0001, ack: int = 0b1111, secondary_header_flag: bool = True,
    ):
        super().__init__(
            service_id=service_id, subservice_id=subservice_id, time=time, ssc=ssc,
            source_data=source_data, apid=apid, message_counter=message_counter,
            space_time_ref=space_time_ref, destination_id=destination_id,
            packet_version=packet_version, pus_version=pus_version, pus_tm_version=pus_tm_version,
            ack=ack, secondary_header_flag=secondary_header_flag
        )

    def append_data_field_header(self, content_list: list):
        """Append important data field header parameters to the passed content list.
        :param content_list:
        :return:
        """
        content_list.append(str(self.service_id))
        content_list.append(str(self.subservice_id))
        content_list.append(str(self.message_counter))
        self.time.add_time_to_content_list(content_list=content_list)

    def append_data_field_header_column_header(self, header_list: list):
        """Append important data field header column headers to the passed list.
        :param header_list:
        :return:
        """
        header_list.append("Service")
        header_list.append("Subservice")
        header_list.append("Subcounter")
        self.time.add_time_headers_to_header_list(header_list=header_list)


class PusTmBase(PusTmInterface):
    def __init__(self, pus_tm: PusTelemetryExtended):
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
    def __init__(self, pus_tm: PusTelemetryExtended):
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
