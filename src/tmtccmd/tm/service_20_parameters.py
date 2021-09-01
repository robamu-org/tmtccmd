from __future__ import annotations
import os
import struct

from tmtccmd.pus.service_list import PusServices
from tmtccmd.ecss.tm import PusTelemetry, PusTmBase, PusTmInfoBase, PusVersion, CdsShortTimestamp
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class ParamStruct:
    def __init__(self):
        self.param_id = 0,
        self.domain_id = 0,
        self.unique_id = 0,
        self.linear_index = 0,
        self.type_ptc = 0
        self.type_pfc = 0
        self.column = 0,
        self.row = 0,
        self.param: any = 0

    def pack(self) -> bytearray:
        pass

    @classmethod
    def unpack(cls, raw_param: bytearray) -> ParamStruct:
        return cls()

class Service20TM(PusTmInfoBase, PusTmBase):
    def __init__(
            self, subservice_id: int, object_id: bytearray, param_id: bytearray,
            domain_id: int, unique_id: int, linear_index: int,
            time: CdsShortTimestamp = None, ssc: int = 0,
            source_data: bytearray = bytearray([]), apid: int = -1, packet_version: int = 0b000,
            pus_version: PusVersion = PusVersion.UNKNOWN, pus_tm_version: int = 0b0001,
            ack: int = 0b1111, secondary_header_flag: bool = True, space_time_ref: int = 0b0000,
            destination_id: int = 0
    ):
        pus_tm = PusTelemetry(
            service_id=PusServices.SERVICE_20_PARAMETER,
            subservice_id=subservice_id,
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
            destination_id=destination_id
        )

        self.object_id = object_id
        self.param_struct = ParamStruct()
        self.__init_without_base(instance=self)
        self.specify_packet_info("Parameter Service Reply")

    @staticmethod
    def __init_without_base(instance: Service20TM):
        tm_data = instance.get_tm_data()
        data_size = len(tm_data)
        if data_size < 4:
            LOGGER.warning("Invalid data length, less than 4")
            return
        elif data_size < 8:
            LOGGER.warning("Invalid data length, less than 8 (Object ID and Parameter ID)")
            return
        else:
            instance.object_id = struct.unpack('!I', tm_data[0:4])[0]
            instance.param_struct.param_id = struct.unpack('!I', tm_data[4:8])[0]
            instance.param_struct.domain_id = tm_data[4]
            instance.param_struct.unique_id = tm_data[5]
            instance.param_struct.linear_index = tm_data[6] << 8 | tm_data[7]

        if instance.get_subservice() == 130:
            # TODO: This needs to be more generic. Furthermore, we need to be able to handle
            #       vector and matrix dumps as well and this is not possible in the current form.
            instance.param_struct.type_ptc = tm_data[8]
            instance.param_struct.type_pfc = tm_data[9]
            instance.param_struct.column = tm_data[10]
            instance.param_struct.row = tm_data[11]
            # TODO: Maybe this should be moved to the ParamStruct class instead
            if data_size > 12:
                if instance.param_struct.type_ptc == 3 and instance.param_struct.type_pfc == 14:
                    instance.param_struct.param = struct.unpack('!I', tm_data[12:16])[0]
                if instance.param_struct.type_ptc == 4 and instance.param_struct.type_pfc == 14:
                    instance.param_struct.param = struct.unpack('!i', tm_data[12:16])[0]
                if instance.param_struct.type_ptc == 5 and instance.param_struct.type_pfc == 1:
                    instance.param_struct.param = struct.unpack('!f', tm_data[12:16])[0]
        else:
            LOGGER.info(
                "Error when receiving Pus Service 20 TM: subservice is not 130"
            )

    @classmethod
    def __empty(cls) -> Service20TM:
        return cls(
            subservice_id=-1,
            object_id=bytearray(4),
            param_id=0,
            domain_id=0,
            unique_id=0,
            linear_index=0
        )

    @classmethod
    def unpack(
            cls, raw_telemetry: bytearray, pus_version: PusVersion = PusVersion.UNKNOWN
    ) -> Service20TM:
        service_20_tm = cls.__empty()
        service_20_tm.pus_tm = PusTelemetry.unpack(
            raw_telemetry=raw_telemetry, pus_version=pus_version
        )
        service_20_tm.__init_without_base(instance=service_20_tm)
        return service_20_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self.object_id))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")

    def get_custom_printout(self) -> str:
        custom_printout = ""
        header_list = []
        content_list = []
        if self.get_subservice() == 130:
            custom_printout = f"Parameter Information:{os.linesep}"
            header_list.append("Domain ID")
            header_list.append("Unique ID")
            header_list.append("Linear Index")
            header_list.append("CCSDS Type")
            header_list.append("Columns")
            header_list.append("Rows")
            # TODO: For more complex parameters like vectors or matrices, special handling would be nice
            header_list.append("Parameter")

            content_list.append(self.domain_id)
            content_list.append(self.unique_id)
            content_list.append(self.linear_index)
            content_list.append("PTC: " + str(self.type_ptc) + " | PFC: " + str(self.type_pfc))
            content_list.append(self.column)
            content_list.append(self.row)
            content_list.append(self.param)

            custom_printout += f"{header_list}{os.linesep}"
            custom_printout += f"{content_list}"
        return custom_printout
