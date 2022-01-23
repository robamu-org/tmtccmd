import collections.abc
from typing import Tuple, Union
from contextlib import contextmanager

from tmtccmd.core.globals_manager import get_global
from tmtccmd.config.definitions import CoreGlobalIds
from tmtccmd.utility.logger import get_console_logger


LOGGER = get_console_logger()


class AnsiColors:
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGNETA = "\x1b[35m"
    CYAN = "\x1b[36m"
    RESET = "\x1b[0m"


def check_args_in_dict(
    param: any, iterable: Union[collections.abc.Iterable, dict], warning_hint: str
) -> Tuple[bool, int]:
    """This functions checks whether the integer representation of a given parameter in
    contained within the passed collections, for example an (integer) enumeration.
    Please note that if the passed parameter has a string representation but is a digit,
    this function will attempt to check whether the integer representation is contained
    inside the passed enumeration.
    :param param:           Value to be checked
    :param iterable:     Enumeration, for example a enum.Enum or enum.IntEnum implementation
    :param warning_hint:
    :return:
    """
    might_be_integer = False
    if param is not None:
        if isinstance(param, str):
            if param.isdigit():
                might_be_integer = True
        elif isinstance(param, int):
            pass
        else:
            LOGGER.warning(f"Passed {warning_hint} type invalid.")
            return False, 0
    else:
        LOGGER.warning(f"No {warning_hint} argument passed.")
        return False, 0

    res_tuple = False, 0
    if isinstance(iterable, dict):
        for idx, enum_value in iterable.items():
            if param == enum_value:
                return True, idx
    else:
        res_tuple = __handle_iterable_non_dict(
            param=param,
            iterable=iterable,
            might_be_integer=might_be_integer,
            init_res_tuple=res_tuple,
        )
    return res_tuple


def __handle_iterable_non_dict(
    param: any,
    iterable: collections.abc.Iterable,
    might_be_integer: bool,
    init_res_tuple: Tuple[bool, any],
) -> (bool, any):
    param_list = list()
    for idx, enum_value in enumerate(iterable):
        if isinstance(enum_value.value, str):
            # Make this case insensitive
            param_list.append(enum_value.value.lower())
        else:
            param_list.append(enum_value.value)
    if param not in param_list:
        if might_be_integer:
            if int(param) in param_list:
                return True, int(param)
        return False, 0
    return init_res_tuple


def print_core_globals():
    """Prints an imporant set of global parameters. Can be used for debugging function
    or as an optional information output
    :return:
    """
    service_param = get_global(CoreGlobalIds.CURRENT_SERVICE)
    mode_param = get_global(CoreGlobalIds.MODE)
    com_if_param = get_global(CoreGlobalIds.COM_IF)
    print(
        f"Current globals | Mode(-m): {mode_param} | Service(-s): {service_param} | "
        f"ComIF(-c): {com_if_param}"
    )


@contextmanager
def acquire_timeout(lock, timeout):
    """Helper functions which allows to check result of the acquire operation while also
    using the context manager.
    :param lock:
    :param timeout:
    :return:
    """
    result = lock.acquire(timeout=timeout)
    yield result
    if result:
        lock.release()
