"""Configuration helpers and definitions.

Submodules:

* :py:mod:`tmtccmd.config.hook` - Base hook class which should be implemented by user and is used
  by the framework to retrieve certain configuration from the user.
* :py:mod:`tmtccmd.config.args` - Various helper methods and classes to create the argument parsers
  and arguments converts to create the data structures expected by this library from passed CLI
  arguments."""

import logging
from pathlib import Path
from typing import Optional

from cfdppy.request import PutRequest
from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import ProxyPutRequest, ProxyPutRequestParams
from spacepackets.util import UnsignedByteField

from tmtccmd.cfdp.request import PutRequestCfgWrapper
from tmtccmd.core import TcMode, TmMode
from tmtccmd.core.base import ModeWrapper
from tmtccmd.tmtc.procedure import (
    CfdpProcedure,
    TreeCommandingProcedure,
    ProcedureWrapper,
    TcProcedureType,
)

from .args import (
    TreeCommandingParams,
    PreArgsParsingWrapper,
    ProcedureParamsWrapper,
    SetupParams,
    add_default_tmtccmd_args,
    create_default_args_parser,
    parse_default_tmtccmd_input_arguments,
)
from .defs import (
    CORE_COM_IF_DICT,
    CfdpParams,
    ComIfDictT,
    CoreComInterfaces,
    CoreModeConverter,
    CoreModeList,
    default_json_path,
)
from .hook import HookBase
from .tmtc import CmdTreeNode


def backend_mode_conversion(mode: str, mode_wrapper: ModeWrapper):
    if mode == CoreModeConverter.get_str(CoreModeList.LISTENER_MODE):
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.IDLE
    elif mode == CoreModeConverter.get_str(CoreModeList.ONE_QUEUE_MODE):
        mode_wrapper.tm_mode = TmMode.LISTENER
        mode_wrapper.tc_mode = TcMode.ONE_QUEUE
    elif mode == CoreModeConverter.get_str(CoreModeList.MULTI_INTERACTIVE_QUEUE_MODE):
        mode_wrapper.tc_mode = TcMode.MULTI_QUEUE
        mode_wrapper.tm_mode = TmMode.LISTENER


class SetupWrapper:
    """This class encapsulates various important setup parameters required by tmtccmd components"""

    def __init__(
        self,
        hook_obj: HookBase,
        setup_params: SetupParams,
        proc_param_wrapper: ProcedureParamsWrapper,
        json_cfg_path: Optional[str] = None,
    ):
        """
        :param hook_obj: User hook object. Needs to be implemented by the user
        :param setup_params: Optional helper wrapper which contains CLI arguments.
        """
        self.hook_obj = hook_obj
        self.json_cfg_path = json_cfg_path
        self._params = setup_params
        self.proc_param_wrapper = proc_param_wrapper
        self.json_cfg_path = json_cfg_path
        if json_cfg_path is None:
            self.json_cfg_path = default_json_path()

    @property
    def params(self):
        return self._params


def tmtc_params_to_procedure(params: TreeCommandingParams) -> TreeCommandingProcedure:
    return TreeCommandingProcedure(cmd_path=params.cmd_path)


def cfdp_put_req_params_to_procedure(params: CfdpParams) -> CfdpProcedure:
    proc_info = CfdpProcedure()
    proc_info.request_wrapper.base = PutRequestCfgWrapper(params)
    return proc_info


def params_to_procedure_conversion(
    param_wrapper: ProcedureParamsWrapper,
) -> ProcedureWrapper:
    proc_wrapper = ProcedureWrapper(None)
    if param_wrapper.ptype == TcProcedureType.TREE_COMMANDING:
        tree_cmd_params = param_wrapper.tree_commanding_params()
        assert tree_cmd_params is not None
        proc_wrapper.procedure = tmtc_params_to_procedure(tree_cmd_params)
    elif param_wrapper.ptype == TcProcedureType.CFDP:
        proc_wrapper.procedure = cfdp_put_req_params_to_procedure(
            param_wrapper.cfdp_params()  # type: ignore
        )
    return proc_wrapper
