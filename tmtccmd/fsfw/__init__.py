import csv
import os
import copy
from typing import Optional, List
from tmtccmd.util.obj_id import ObjectIdU32, ObjectIdDictT
from tmtccmd.pus.s5_event import EventInfo, EventDictT
from tmtccmd.util.retval import RetvalDictT, RetvalInfo


def parse_fsfw_objects_csv(csv_file: str) -> Optional[ObjectIdDictT]:
    if os.path.exists(csv_file):
        obj_id_dict = dict()
        obj_id = ObjectIdU32(obj_id=0)
        with open(csv_file) as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=";")
            for row in csv_reader:
                # Parse hex string
                obj_id.obj_id = int(row[0], 16)
                obj_id.name = row[1]
                obj_id_dict.update({obj_id.as_bytes: copy.copy(obj_id)})
        return obj_id_dict
    else:
        return None


def parse_fsfw_events_csv(csv_file: str) -> Optional[EventDictT]:
    if os.path.exists(csv_file):
        event_dict = dict()
        with open(csv_file) as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=";")
            info = EventInfo()
            for idx, row in enumerate(csv_reader):
                if idx == 0:
                    continue
                info.id = int(row[0])
                info.name = row[2]
                info.severity = row[3]
                info.info = row[4]
                info.file_location = row[5]
                event_dict.update({info.id: copy.copy(info)})
        return event_dict
    else:
        return None


def parse_fsfw_returnvalues_csv(csv_file: str) -> Optional[RetvalDictT]:
    if os.path.exists(csv_file):
        retval_dict = dict()
        with open(csv_file) as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=";")
            info = RetvalInfo()
            for idx, row in enumerate(csv_reader):
                if idx == 0:
                    continue
                # Parse hex
                id_col = str(row[0])
                if "0x" in id_col:
                    info.id = int(id_col, 0)
                else:
                    info.id = int(id_col, 16)
                info.name = row[1]
                info.info = row[2]
                info.if_name = row[5]
                retval_dict.update({info.id: copy.copy(info)})
        return retval_dict
    else:
        return None


def bit_extractor(byte: int, position: int):
    """

    :param byte:
    :param position:
    :return:
    """
    shift_number = position + (6 - 2 * (position - 1))
    return (byte >> shift_number) & 1


def validity_buffer_list(validity_buffer: bytes, num_vars: int) -> List[bool]:
    """
    :param validity_buffer: Validity buffer in bytes format
    :param num_vars: Number of variables
    :return:
    """
    valid_list = []
    counter = 0
    for index, byte in enumerate(validity_buffer):
        for bit in range(1, 9):
            if bit_extractor(byte, bit) == 1:
                valid_list.append(True)
            else:
                valid_list.append(False)
            counter += 1
            if counter == num_vars:
                return valid_list
    return valid_list
