"""Base class for Service 200 mode commanding reply handling.
"""
from __future__ import annotations
import struct
from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry

from tmtccmd.pus.definitions import CustomPusServices
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase


class Service200TM(PusTmBase, PusTmInfoBase):
    def __init__(
        self,
        subservice_id: int,
        object_id: bytearray,
        return_value: int = 0,
        mode: int = 0,
        submode: int = 0,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        source_data: bytearray = bytearray([]),
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        pus_tm_version: int = 0b0001,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        source_data = bytearray()
        source_data.extend(object_id)
        if subservice_id == 7:
            source_data.extend(struct.pack("!H", return_value))
        elif subservice_id == 6 or subservice_id == 8:
            source_data.extend(struct.pack("!I", mode))
            source_data.append(submode)
        pus_tm = PusTelemetry(
            service=CustomPusServices.SERVICE_200_MODE,
            subservice=subservice_id,
            time=time,
            ssc=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            pus_version=pus_version,
            secondary_header_flag=secondary_header_flag,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        self.set_packet_info("Mode Reply")

        self.is_cant_reach_mode_reply = False
        self.is_mode_reply = False
        self.object_id = object_id
        self.mode = mode
        self.submode = submode
        self.return_value = return_value
        self.__init_without_base(instance=self)

    @staticmethod
    def __init_without_base(instance: Service200TM):
        tm_data = instance.tm_data
        instance.object_id = tm_data[0:4]
        if instance.subservice == 7:
            instance.append_packet_info(": Can't reach mode")
            instance.is_cant_reach_mode_reply = True
            instance.return_value = tm_data[4] << 8 | tm_data[5]
        elif instance.subservice == 6 or instance.subservice == 8:
            instance.is_mode_reply = True
            if instance.subservice == 8:
                instance.append_packet_info(": Wrong Mode")
            elif instance.subservice == 6:
                instance.append_packet_info(": Mode reached")
            instance.mode = struct.unpack("!I", tm_data[4:8])[0]
            instance.submode = tm_data[8]

    @classmethod
    def __empty(cls) -> Service200TM:
        return cls(subservice_id=0, object_id=bytearray(4))

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ) -> Service200TM:
        service_200_tm = cls.__empty()
        service_200_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        service_200_tm.__init_without_base(instance=service_200_tm)
        return service_200_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        object_id_num = struct.unpack("!I", self.object_id)[0]
        content_list.append(f"0x{object_id_num:08x}")
        if self.is_cant_reach_mode_reply:
            content_list.append(hex(self.return_value))
        elif self.is_mode_reply:
            if self.mode == 1:
                mode_string = "ON"
            elif self.mode == 2:
                mode_string = "NORMAL"
            elif self.mode == 3:
                mode_string = "RAW"
            elif self.mode == 0:
                mode_string = "OFF"
            else:
                mode_string = f"UNKNOWN ({self.mode})"
            content_list.append(mode_string)
            content_list.append(str(self.submode))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        if self.is_cant_reach_mode_reply:
            header_list.append("Return Value")
        elif self.is_mode_reply:
            header_list.append("Mode")
            header_list.append("Submode")
