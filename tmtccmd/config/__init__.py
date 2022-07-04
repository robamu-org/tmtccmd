"""Definitions for the TMTC commander core
"""
from typing import Optional

from tmtccmd.core import ModeWrapper, TmMode, TcMode

from .args import (
    SetupParams,
    create_default_args_parser,
    add_default_tmtccmd_args,
    parse_default_tmtccmd_input_arguments,
    DefProcedureParams,
    ArgParserWrapper,
)
from .defs import (
    CoreModeList,
    CoreModeStrings,
    CoreComInterfaces,
    CORE_COM_IF_DICT,
    default_json_path,
    CoreServiceList,
    ComIfDictT,
)
from .prompt import prompt_op_code, prompt_service
from .tmtc import TmTcDefWrapper
from .hook import TmTcCfgHookBase


def backend_mode_conversion(mode: CoreModeList, mode_wrapper: ModeWrapper):
    if mode == CoreModeStrings[CoreModeList.LISTENER_MODE]:
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.IDLE
    elif mode == CoreModeStrings[CoreModeList.ONE_QUEUE_MODE]:
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.ONE_QUEUE
    elif mode == CoreModeStrings[CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE]:
        mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
        mode_wrapper.tm_mode = TmMode.LISTENER


def get_global_hook_obj() -> Optional[TmTcCfgHookBase]:
    """This function can be used to get the handle to the global hook object.
    :return:
    """
    from tmtccmd import get_console_logger

    logger = get_console_logger()
    try:
        from tmtccmd.core.globals_manager import get_global
        from tmtccmd.config.definitions import CoreGlobalIds

        from typing import cast

        hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
        if hook_obj_raw is None:
            logger.error("Hook object is invalid!")
            return None
        return cast(TmTcCfgHookBase, hook_obj_raw)
    except ImportError:
        logger.exception("Issues importing modules to get global hook handle!")
        return None
    except AttributeError:
        logger.exception("Attribute error when trying to get global hook handle!")
        return None


class SetupWrapper:
    """This class encapsulates various important setup parameters required by tmtccmd components"""

    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        setup_params: SetupParams,
        json_cfg_path: Optional[str] = None,
    ):
        """
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param setup_params: Optional helper wrapper which contains CLI arguments.
        """
        self.hook_obj = hook_obj
        self.json_cfg_path = json_cfg_path
        self._params = setup_params
        self.json_cfg_path = json_cfg_path
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()

    @property
    def params(self):
        return self._params
