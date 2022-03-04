import csv
import os
import copy
from typing import Optional
from tmtccmd.pus.obj_id import ObjectId, ObjectIdDictT
from tmtccmd.pus.service_5_event import EventInfo, str_to_severity, EventDictT
from tmtccmd.utility.retval import RetvalDictT, RetvalInfo


def parse_fsfw_objects_csv(csv_file: str) -> Optional[ObjectIdDictT]:
    if os.path.exists(csv_file):
        obj_id_dict = dict()
        obj_id = ObjectId(object_id=0)
        with open(csv_file) as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=";")
            for row in csv_reader:
                # Parse hex string
                obj_id.id = int(row[0], 16)
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
            for row in csv_reader:
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
            for row in csv_reader:
                # Parse hex string
                info.id = int(row[0], 16)
                info.name = row[1]
                info.info = row[2]
                info.if_name = row[5]
                retval_dict.update({info.id: copy.copy(info)})
        return retval_dict
    else:
        return None
