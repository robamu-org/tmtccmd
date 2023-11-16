from __future__ import annotations

import enum
import os
from typing import Any, Dict, List, Optional, Tuple, Union

from spacepackets.cfdp.pdu.helper import deprecation

from tmtccmd.version import get_version


class TreePart(enum.Enum):
    EDGE = "├──"
    LINE = "│  "
    CORNER = "└──"
    BLANK = "   "


class CmdTreeNode:
    def __init__(
        self, name: str, description: str, parent: Optional[CmdTreeNode] = None
    ) -> None:
        self.name = name
        self.desc = description
        self.parent: Optional[CmdTreeNode] = parent
        self.children: List[CmdTreeNode] = []

    @classmethod
    def root_node(cls) -> CmdTreeNode:
        return cls(name="/", description="Root Node", parent=None)

    def add_child(self, child: CmdTreeNode):
        child.parent = self
        self.children.append(child)

    @property
    def name_dict(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Returns a nested dictionary where the key is always the name of the node, and the
        value is one nested name dictionary for each child node."""
        children_dict = {}
        if self.children:
            for child in self.children:
                children_dict.update(child.name_dict)
            return {self.name: children_dict}
        return {self.name: None}

    def str_for_tree(self, with_description: bool) -> str:
        return self.__str_for_depth(with_description, False, 0)

    def __str_for_depth(
        self, with_description: bool, last_child: bool, depth: int
    ) -> str:
        string = ""

        def core_string_handler(string: str) -> str:
            string += self.name + " "
            if with_description:
                string += "[ " + self.desc + " ] "
            string += os.linesep
            for idx, child in enumerate(self.children):
                # Use recursion here to get the string for the subtree.
                if idx == len(self.children) - 1:
                    string += child.__str_for_depth(with_description, True, depth + 1)
                else:
                    string += child.__str_for_depth(with_description, False, depth + 1)
            return string

        if depth == 0:
            return core_string_handler(string)
        # If we are at a larger depth than 0, we want to prepend the name using a special
        # format. Example:
        # /
        # |
        # /
        # ├── ACS
        # │  └── ACS_CTRL
        # └── TCS
        for i in range(depth):
            if i == depth - 1:
                if last_child:
                    string += TreePart.CORNER.value
                else:
                    string += TreePart.EDGE.value
            elif i == 0:
                string += TreePart.LINE.value
            else:
                string += TreePart.BLANK.value
        string += " "
        return core_string_handler(string)

    def __str__(self) -> str:
        return self.str_for_tree(False)


ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
OpCodeInfoT = str


@deprecation.deprecated(
    deprecated_in="8.0.0",
    details="use the new command definition tree instead",
    current_version=get_version(),
)
class OpCodeOptionBase:
    def __init__(self):
        pass


OpCodeDict = Dict[str, Tuple[OpCodeInfoT, OpCodeOptionBase]]


@deprecation.deprecated(
    deprecated_in="8.0.0",
    details="use the new command definition tree instead",
    current_version=get_version(),
)
class OpCodeEntry:
    def __init__(self):
        self._op_code_dict_num_keys: OpCodeDict = dict()
        self._op_code_dict_str_keys: OpCodeDict = dict()

    def add(
        self,
        keys: OpCodeNameT,
        info: str,
        options: OpCodeOptionBase = OpCodeOptionBase(),
    ):
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            if key.isdigit():
                self._op_code_dict_num_keys.update({key: (info, options)})
            else:
                self._op_code_dict_str_keys.update({key: (info, options)})

    def sort_num_key_dict(self):
        self._op_code_dict_num_keys = {
            int(k): v for k, v in self._op_code_dict_num_keys.items()
        }

    def sort_text_key_dict(self):
        self._op_code_dict_str_keys = {
            k: v for k, v in sorted(self._op_code_dict_str_keys.items())
        }

    def info(self, op_code: str) -> Optional[str]:
        if op_code.isdigit():
            entry_tuple = self._op_code_dict_num_keys.get(op_code)
            if entry_tuple is not None:
                return entry_tuple[0]

        entry_tuple = self._op_code_dict_str_keys.get(op_code)
        if entry_tuple is not None:
            return entry_tuple[0]
        return None

    def __str__(self):
        return (
            f"Op codes with numeric keys: {self._op_code_dict_num_keys!r}), "
            f"op codes with text keys: {self._op_code_dict_str_keys!r}"
        )

    @property
    def op_code_dict_num_keys(self):
        return self._op_code_dict_num_keys

    @property
    def op_code_dict_str_keys(self):
        return self._op_code_dict_str_keys


# It is possible to specify a service without any op codes
ServiceDictValueT = Optional[Tuple[ServiceInfoT, OpCodeEntry]]
ServiceOpCodeDictT = Dict[ServiceNameT, ServiceDictValueT]


@deprecation.deprecated(
    deprecated_in="8.0.0",
    details="use the new command definition tree instead",
    current_version=get_version(),
)
class TmtcDefinitionWrapper:
    def __init__(self, init_defs: Optional[ServiceOpCodeDictT] = None):
        if init_defs is None:
            self.defs: ServiceOpCodeDictT = dict()
        else:
            self.defs = init_defs

    def __repr__(self):
        return f"{self.__class__.__name__}(init_defs={self.defs!r}"

    def add_service(
        self,
        name: str,
        info: str,
        op_code_entry: OpCodeEntry,
    ):
        self.defs.update({name: (info, op_code_entry)})

    def op_code_entry(self, service_name: str) -> Optional[OpCodeEntry]:
        srv_entry = self.defs.get(service_name)
        if srv_entry is not None:
            return srv_entry[1]
        return None

    def sort(self):
        self.defs = {key: self.defs[key] for key in sorted(self.defs.keys())}


REGISTER_CBS = set()


@deprecation.deprecated(
    deprecated_in="8.0.0",
    details="use the new command definition tree instead",
    current_version=get_version(),
)
def tmtc_definitions_provider(adder_func):
    """Function decorator which registers the decorated function to be a TMTC definition provider.
    The :py:func:`execute_tmtc_def_functions` function can be used to call all functions.

    It is expected that the decorated function takes the py:class:`TmTcDefWrapper` as the first
    argument. The user can pass any additional arguments as positional and keyword
    arguments.
    """
    global REGISTER_CBS

    def call_explicitely(defs: TmtcDefinitionWrapper, *args, **kwargs):
        if REGISTER_CBS and adder_func in REGISTER_CBS:
            REGISTER_CBS.remove(adder_func)
        print(f"{adder_func.__name__} called explicitely, not necessary")
        return adder_func(defs, args, kwargs)

    REGISTER_CBS.add(adder_func)
    return call_explicitely


@deprecation.deprecated(
    deprecated_in="8.0.0",
    details="use the new command definition tree instead",
    current_version=get_version(),
)
def call_all_definitions_providers(defs: TmtcDefinitionWrapper, *args, **kwargs):
    global REGISTER_CBS
    if REGISTER_CBS:
        for register_cb in REGISTER_CBS.copy():
            if args and kwargs:
                register_cb(defs, args, kwargs)
            if args and not kwargs:
                register_cb(defs, args)
            elif not args and not kwargs:
                register_cb(defs)
            REGISTER_CBS.remove(register_cb)
