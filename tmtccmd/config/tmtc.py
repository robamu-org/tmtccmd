from __future__ import annotations

import enum
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from deprecated.sphinx import deprecated


class TreePart(enum.Enum):
    EDGE = "├──"
    LINE = "│  "
    CORNER = "└──"
    BLANK = "   "


class DepthInfo:
    def __init__(
        self,
        depth: int,
        last_child: bool,
        max_depth: Optional[int] = None,
        layer_is_last_set: Optional[Set[int]] = None,
    ) -> None:
        self.depth = depth
        self.last_child = last_child
        if layer_is_last_set is None:
            self.layer_is_last_set = set()
        else:
            self.layer_is_last_set = layer_is_last_set
        self.max_depth = max_depth

    def is_layer_for_last_child(self, depth: int) -> bool:
        return depth in self.layer_is_last_set

    def set_layer_is_last_child(self, depth: int):
        self.layer_is_last_set.add(depth)


class CmdTreeNode:
    def __init__(
        self, name: str, description: str, parent: Optional[CmdTreeNode] = None
    ) -> None:
        self.name = name
        self.description = description
        self.parent: Optional[CmdTreeNode] = parent
        self.children: Dict[str, CmdTreeNode] = {}

    @classmethod
    def root_node(cls) -> CmdTreeNode:
        return cls(name="/", description="Root Node", parent=None)

    def __getitem__(self, arg):
        return self.children[arg]

    def add_child(self, child: CmdTreeNode):
        child.parent = self
        self.children.update({child.name: child})

    def contains_path(self, path: str) -> bool:
        """Check whether a full slash separated command path is contained within
        the command tree."""
        return self.contains_path_from_node_list(path.split("/"))

    def contains_path_from_node_list(self, node_name_list: List[str]) -> bool:
        """Check whether the given list of nodes are contained within the command tree."""
        if len(node_name_list) == 0:
            return False
        # Only root node.
        if len(node_name_list) == 2 and node_name_list == ["", ""]:
            return True
        if node_name_list[0] == "":
            # Cut off empty string left of root node /
            node_name_list = node_name_list[1:]
        for child in self.children.values():
            if node_name_list[0] == child.name:
                # This is the last node.
                if len(node_name_list) == 1:
                    return True
                return child.contains_path_from_node_list(node_name_list[1:])
        return False

    @property
    def name_dict(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Returns a nested dictionary where the key is always the name of the node, and the
        value is one nested name dictionary for each child node."""
        children_dict = {}
        if self.children:
            for child in self.children.values():
                children_dict.update(child.name_dict)
            return {self.name: children_dict}
        return {self.name: None}

    def str_for_tree(
        self, with_description: bool, max_depth: Optional[int] = None
    ) -> str:
        return self.__str_for_depth(
            with_description, DepthInfo(depth=0, last_child=False, max_depth=max_depth)
        )

    def __str_for_depth(self, with_description: bool, depth_info: DepthInfo) -> str:
        line = ""
        # If we are at a larger depth than 0, we want to prepend the name using a special
        # format. Example:
        #
        # Example 1:
        # /
        # ├── ACS
        # │  └── ACS_CTRL
        # └── TCS
        #
        # Example 2:
        # /
        # ├── ACS
        # │  └── ACS_CTRL
        # └── TCS
        #    └── TCS_CTRL
        #
        # Example 3:
        # /
        # ├── ACS
        # │  ├── ACS_CTRL
        # │  └── MGM_0
        # │     └── UPDATE_CFG
        # ├── TCS
        # │  ├── TCS_CTRL
        # │  └── PT1000_0
        # └── PING
        for i in range(depth_info.depth):
            if i == depth_info.depth - 1:
                if depth_info.last_child:
                    line += TreePart.CORNER.value + " "
                else:
                    line += TreePart.EDGE.value + " "
            else:
                if depth_info.is_layer_for_last_child(i):
                    line += TreePart.BLANK.value
                else:
                    line += TreePart.LINE.value
        if depth_info.max_depth is not None and depth_info.depth > depth_info.max_depth:
            line += f"... (cut-off, maximum depth {depth_info.max_depth}){os.linesep}"
            return line
        else:
            line += self.name
            if with_description:
                line = f"{line.ljust(35)} [ " + self.description + " ]"
        string = line + os.linesep
        for idx, child in enumerate(self.children.values()):
            last_child = True if (idx == (len(self.children) - 1)) else False
            child_depth_info = DepthInfo(
                depth=depth_info.depth + 1,
                last_child=last_child,
                max_depth=depth_info.max_depth,
                layer_is_last_set=depth_info.layer_is_last_set,
            )
            if last_child:
                child_depth_info.set_layer_is_last_child(depth_info.depth)
            # Use recursion here to get the string for the subtree.
            string += child.__str_for_depth(with_description, child_depth_info)
        return string

    def __str__(self) -> str:
        return self.str_for_tree(False)


ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
OpCodeInfoT = str


@deprecated(
    version="8.0.0",
    reason="use the new command definition tree instead",
)
class OpCodeOptionBase:
    def __init__(self):
        pass


OpCodeDict = Dict[str, Tuple[OpCodeInfoT, OpCodeOptionBase]]


@deprecated(
    version="8.0.0",
    reason="use the new command definition tree instead",
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


@deprecated(
    version="8.0.0",
    reason="use the new command definition tree instead",
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


@deprecated(
    version="8.0.0",
    reason="use the new command definition tree instead",
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


@deprecated(
    version="8.0.0",
    reason="use the new command definition tree instead",
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
