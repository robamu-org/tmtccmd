import os
import struct

from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.utility.logger import get_console_logger

logger = get_console_logger()


class Service20TM(PusTelemetry):
    def __init__(self, byte_array):
        super().__init__(byte_array)
        data_size = len(self._tm_data)
        self.objectId = 0
        self.parameter_id = 0
        self.domain_id = 0
        self.unique_id = 0
        self.linear_index = 0

        if data_size < 4:
            logger.warning("Service20TM: Invalid data length, less than 4")
            return
        elif data_size < 8:
            logger.warning("Service20TM: Invalid data length, less than 8 (Object ID and Parameter ID)")
            return
        else:
            self.objectId = struct.unpack('!I', self._tm_data[0:4])[0]
            self.parameter_id = struct.unpack('!I', self._tm_data[4:8])[0]
            self.domain_id = self._tm_data[4]
            self.unique_id = self._tm_data[5]
            self.linear_index = self._tm_data[6] << 8 | self._tm_data[7]

        self.param = 0
        if self.get_subservice() == 130:
            # TODO: This needs to be more generic. Furthermore, we need to be able to handle vector and matrix
            #       dumps as well and this is not possible in the current form.
            self.type = struct.unpack('!H', self._tm_data[8:10])[0]
            self.type_ptc = self._tm_data[8]
            self.type_pfc = self._tm_data[9]
            self.column = self._tm_data[10]
            self.row = self._tm_data[11]
            if len(self._tm_data) > 12:
                if self.type_ptc == 3 and self.type_pfc == 14:
                    self.param = struct.unpack('!I', self._tm_data[12:16])[0]
                if self.type_ptc == 4 and self.type_pfc == 14:
                    self.param = struct.unpack('!i', self._tm_data[12:16])[0]
                if self.type_ptc == 5 and self.type_pfc == 1:
                    self.param = struct.unpack('!f', self._tm_data[12:16])[0]
        else:
            logger.info(
                "Error when receiving Pus Service 20 TM: subservice is not 130"
            )
        self.specify_packet_info("Parameter Service Reply")

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self.objectId))
        # array.append(f"{self.parameter_id:#010x}")
        content_list.append(self.domain_id)
        content_list.append(self.unique_id)
        content_list.append(self.linear_index)

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
