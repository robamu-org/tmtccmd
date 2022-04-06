from tmtccmd.logging import get_console_logger

APID = 0xEF
LOGGER = get_console_logger()


def pre_send_cb(data: bytes, user_args: any):
    LOGGER.info(f"Sending TC with {len(data)} bytes")
