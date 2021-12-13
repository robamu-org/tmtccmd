from __future__ import annotations
import struct

from spacepackets.ecss.definitions import PusServices
from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry

from tmtccmd.tm.base import PusTmInfoBase, PusTmBase
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class FileInfo:
    def __init__(
        self,
        file_name: str,
        repo_path: str,
        file_size: int = 0,
        lock_status: bool = False,
    ):
        self.file_name = file_name
        self.repo_path = repo_path
        self.file_size = file_size
        self.lock_status = lock_status


class Service23TM(PusTmInfoBase, PusTmBase):
    MAX_REPOSITORY_LENGTH = 64
    MAX_FILENAME_LENGTH = 12

    def __init__(
        self,
        subservice_id: int,
        object_id: bytearray,
        repo_path: str,
        file_name: str,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        pus_tm_version: int = 0b0001,
        ack: int = 0b1111,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        self.object_id = object_id
        self.data_start_idx = 0
        self.file_info = FileInfo(file_name=file_name, repo_path=repo_path)
        pus_tm = PusTelemetry(
            service=PusServices.SERVICE_23_FILE_MGMT,
            subservice=subservice_id,
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
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)

        self.specify_packet_info("File Service Reply")

    @staticmethod
    def __init_without_base(instance: Service23TM):
        tm_data = instance.get_tm_data()
        if len(tm_data) < 4:
            LOGGER.error("Service23TM: Invalid packet format!")
            return
        instance.object_id = struct.unpack("!I", tm_data[0:4])[0]
        instance.file_info.file_size = 0
        instance.file_info.lock_status = False
        instance.data_start_idx = 0
        if instance.get_subservice() == 4:
            instance.unpack_repo_and_filename()
            instance.unpack_file_attributes()
        elif instance.get_subservice() == 132:
            instance.unpack_repo_and_filename()

    @classmethod
    def __empty(cls) -> Service23TM:
        return cls(subservice_id=-1, object_id=bytearray(4), repo_path="", file_name="")

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service23TM:
        service_23_tm = cls.__empty()
        service_23_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        service_23_tm.__init_without_base(instance=service_23_tm)
        return service_23_tm

    def unpack_repo_and_filename(self):
        tm_data = self.get_tm_data()
        repo_path_found = False
        path_idx_start = 0
        max_len_to_scan = len(self.get_tm_data()) - 4
        for idx in range(4, max_len_to_scan):
            if not repo_path_found and tm_data[idx] == 0:
                repo_bytes = tm_data[4:idx]
                self.file_info.repo_path = repo_bytes.decode("utf-8")
                path_idx_start = idx + 1
                idx += 1
                repo_path_found = True
            if repo_path_found:
                if tm_data[idx] == 0:
                    filename_bytes = tm_data[path_idx_start:idx]
                    self.file_info.file_name = filename_bytes.decode("utf-8")
                    self.data_start_idx = idx + 1
                    break

    def unpack_file_attributes(self):
        # Size of file length (4) + lock status (1), adapt if more field are added!
        print(len(self.get_tm_data()) - self.data_start_idx)
        if len(self.get_tm_data()) - self.data_start_idx != 5:
            LOGGER.error("Service23TM: Invalid lenght of file attributes data")
            return
        self.file_info.file_size = struct.unpack(
            "!I", self.get_tm_data()[self.data_start_idx : self.data_start_idx + 4]
        )[0]
        self.file_info.lock_status = self.get_tm_data()[self.data_start_idx + 4]

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list)
        content_list.append(self.object_id)
        content_list.append(self.file_info.repo_path)
        content_list.append(self.file_info.file_name)
        if self.get_subservice() == 4:
            content_list.append(self.file_info.file_size)
            if self.file_info.lock_status == 0:
                content_list.append("No")
            else:
                content_list.append("Yes")

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list)
        header_list.append("Object ID")
        header_list.append("Repo Path")
        header_list.append("File Name")
        if self.get_subservice() == 4:
            header_list.append("File Size")
            header_list.append("Locked")
