import os
import logging
from datetime import datetime
from tmtccmd.logging import LOG_DIR

BASE_FILE_NAME = "events"


def get_event_file_logger():
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
    # This should create a unique event log file for most cases. If for some reason this is called
    # with the same name, the events will appended to an old file which was created in the same
    # second. This is okay.
    file_name = f"{BASE_FILE_NAME}_{datetime.now().date()}_{datetime.now().time().replace(':', '')}"
    logging.basicConfig(filename=file_name)


def event_service_print_utility():
    pass
