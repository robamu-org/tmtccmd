"""In case ECSS and CFDP code go into a separate pyton package, this layer can be adapted
to use a different logger (e.g. default logger)
"""
from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()
