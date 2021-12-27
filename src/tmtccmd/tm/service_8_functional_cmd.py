"""Contains classes and functions to handle PUS Service 8 telemetry.
"""
from __future__ import annotations
import struct

from spacepackets.ecss.tm import CdsShortTimestamp, PusVersion, PusTelemetry
from tmtccmd.tm.base import PusTmInfoBase, PusTmBase
from tmtccmd.pus import ObjectId
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class Service8TM(PusTmBase, PusTmInfoBase):
    def __init__(
        self,
        subservice_id: int,
        object_id: bytearray,
        action_id: int,
        custom_data: bytearray,
        time: CdsShortTimestamp = None,
        ssc: int = 0,
        apid: int = -1,
        packet_version: int = 0b000,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
        secondary_header_flag: bool = True,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        """This class can be used to deserialize service 8 packets.
        :param raw_telemetry:      Raw bytearray which will be deserialized
        :param call_srv8_hook:
        :raises ValueError: If the length of the passed bytearray is too short.
        """
        self._object_id = ObjectId.from_bytes(obj_id_as_bytes=object_id)
        self._action_id = action_id
        self._custom_data = custom_data
        source_data = bytearray()
        source_data.extend(object_id)
        source_data.extend(struct.pack("!I", self._action_id))
        source_data.extend(self._custom_data)
        pus_tm = PusTelemetry(
            service=5,
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
        self.__init_without_base(instance=self)

    @staticmethod
    def __init_without_base(instance: Service8TM):
        if instance.subservice == 130:
            tm_data = instance.tm_data
            if len(tm_data) < 8:
                LOGGER.warning(
                    f"Length of Service 8 TM data field {len(tm_data)} short than 8"
                )
                raise ValueError
            instance.set_packet_info("Functional Data Reply")
            instance._object_id = ObjectId.from_bytes(obj_id_as_bytes=tm_data[0:4])
            instance._action_id = struct.unpack("!I", tm_data[4:8])[0]
            instance._custom_data = tm_data[8:]
        else:
            instance.set_packet_info("Unknown functional commanding reply")

    @classmethod
    def __empty(cls) -> Service8TM:
        return cls(
            subservice_id=-1,
            object_id=bytearray(4),
            action_id=0,
            custom_data=bytearray(),
        )

    @classmethod
    def unpack(
        cls,
        raw_telemetry: bytearray,
        pus_version: PusVersion = PusVersion.GLOBAL_CONFIG,
    ):
        service_8_tm = cls.__empty()
        service_8_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        service_8_tm.__init_without_base(instance=service_8_tm)
        return service_8_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(self._object_id.as_string)
        content_list.append(self._action_id)

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        header_list.append("Action ID")

    @property
    def source_object_id_as_bytes(self) -> bytes:
        return self._object_id.as_bytes

    @property
    def source_object_id(self) -> int:
        return self._object_id.as_int

    @property
    def action_id(self) -> int:
        return self._action_id

    @property
    def custom_data(self) -> bytearray:
        return self._custom_data
