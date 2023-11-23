from __future__ import annotations

import enum
import copy
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
            self.set_of_layers_where_child_is_last = set()
        else:
            self.set_of_layers_where_child_is_last = layer_is_last_set
        self.max_depth = max_depth

    def is_layer_for_last_child(self, depth: int) -> bool:
        return depth in self.set_of_layers_where_child_is_last

    def set_layer_is_last_child(self, depth: int):
        self.set_of_layers_where_child_is_last.add(depth)

    def clear_layer_is_last_child(self, depth: int):
        self.set_of_layers_where_child_is_last.remove(depth)


class CmdTreeNode:
    """The command tree node is the primary data structure used to specify the command
    structure in a way it can be used by framework components.

    The node class provides an API which allows to build a tree of command nodes. Generally, a full
    path from the root node to a leaf will be the command identifier or command path for executing
    a certain command or procedure.

    You can create the root node using the :py:meth:`CmdTreeNode.root_node` class method. After
    that children can be appended to the nodes using the :py:meth:`CmdTreeNode.add_child` method.

    You can use square bracket operator to access the children of a node directly. For example,
    if a node with the name ``test_node`` has the child ``event``, you could use
    ``test_node["event"]`` to access the child node.

    """

    def __init__(
        self,
        name: str,
        description: str,
        parent: Optional[CmdTreeNode] = None,
        hide_children_for_print: bool = False,
        hide_children_which_are_leaves: bool = False,
    ) -> None:
        """
        Parameters
        ------------

        name
            Name of the node, which will be also part of the command path when picking a path
            through the tree.
        description
            Additional description for the node.
        parent
            Parent of the node. Generally, this does not need to be set, as it will be set
            correctly when using the :py:meth:`CmdTreeNode.add_child` method.
        hide_children_for_print
            For large tree, it can make sense to hide the children for a regular printout of the
            tree. This field allows to do this.
        hide_children_which_are_leaves
            For large tree, it can make sense to hide the children which are leaves for a regular
            printout of the tree. This field allows to do this. This field is overriden by the
            strong ``hide_children_for_print`` field.

        """
        self.name = name
        self.description = description
        self.parent: Optional[CmdTreeNode] = parent
        self.children: Dict[str, CmdTreeNode] = {}
        self.hide_children_for_print = hide_children_for_print
        self.hide_children_which_are_leaves = hide_children_which_are_leaves

    @classmethod
    def root_node(cls) -> CmdTreeNode:
        return cls(name="/", description="Root Node", parent=None)

    def __getitem__(self, arg):
        return self.children[arg]

    def add_child(self, child: CmdTreeNode):
        """Add a child to the node. This will also assign the parent class of the child to
        the current node."""
        child.parent = self
        self.children.update({child.name: child})

    def is_leaf(self) -> bool:
        """A leaf is a node which has no children."""
        return len(self.children) == 0

    def contains_path(self, path: str) -> bool:
        """Check whether a full slash separated command path is contained within
        the command tree."""
        if path == "":
            return False
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

    def extract_subnode(self, path: str) -> Optional[CmdTreeNode]:
        """Extract a subnode given a relative path."""
        if path == "":
            return None
        return self.extract_subnode_by_node_list(path.split("/"))

    def extract_subnode_by_node_list(
        self, node_list: List[str]
    ) -> Optional[CmdTreeNode]:
        """Extract a subnode given a list which would form a relative path if it were joined
        using slashes."""
        if not self.contains_path_from_node_list(node_list):
            return None
        if len(node_list) == 1 and self.children[node_list[0]] is not None:
            return self.children[node_list[0]]
        return self.children[node_list[0]].extract_subnode_by_node_list(node_list[1:])

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
        self,
        with_description: bool,
        max_depth: Optional[int] = None,
        show_hidden_elements: bool = False,
    ) -> str:
        """Retrieve the a human readable printout of the tree.

        Parameters
        ------------

        with_description
            Display descriptions right to the tree.
        max_depth
            Entries will be cut-off at the specified depth. None can be specified to print all
            depths.
        show_hidden_elements
            Overrides the hide argument of command tree nodes.
        """
        return self.__str_for_depth(
            with_description,
            DepthInfo(depth=0, last_child=False, max_depth=max_depth),
            show_hidden_elements=show_hidden_elements,
        )

    def __str_for_depth(
        self,
        with_description: bool,
        depth_info: DepthInfo,
        show_hidden_elements: bool = False,
    ) -> str:
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
        line = CmdTreeNode._create_leading_tree_part(depth_info)
        if depth_info.max_depth is not None and depth_info.depth > depth_info.max_depth:
            line += f"... (cut-off, maximum depth {depth_info.max_depth}){os.linesep}"
            return line
        else:
            line += self.name
            if with_description:
                line = f"{line.ljust(35)} [ " + self.description + " ]"
        string = line + os.linesep
        return self._handle_children_printout(
            string, with_description, depth_info, show_hidden_elements
        )

    @staticmethod
    def _create_leading_tree_part(depth_info: DepthInfo) -> str:
        line = ""
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
        return line

    def _handle_children_printout(
        self,
        string: str,
        with_description: bool,
        depth_info: DepthInfo,
        show_hidden_elements: bool,
    ) -> str:
        child_depth_info = DepthInfo(
            depth=depth_info.depth + 1,
            last_child=False,
            max_depth=depth_info.max_depth,
            layer_is_last_set=copy.copy(depth_info.set_of_layers_where_child_is_last),
        )
        if (
            not show_hidden_elements
            and self.hide_children_for_print
            and len(self.children) > 0
        ):
            CmdTreeNode._this_is_the_last_child(child_depth_info, depth_info)
            string += CmdTreeNode._create_supressed_children_line(
                child_depth_info, "children are hidden"
            )
        else:
            if not show_hidden_elements and self.hide_children_which_are_leaves:
                str_if_there_are_leaves = (
                    self._handle_children_output_suppressed_leaves(
                        with_description, depth_info, child_depth_info
                    )
                )
                if str_if_there_are_leaves is not None:
                    return string + str_if_there_are_leaves
            for idx, child in enumerate(self.children.values()):
                if idx == len(self.children) - 1:
                    CmdTreeNode._this_is_the_last_child(child_depth_info, depth_info)
                # Use recursion here to get the string for the subtree.
                string += child.__str_for_depth(
                    with_description=with_description,
                    depth_info=child_depth_info,
                    show_hidden_elements=show_hidden_elements,
                )
        return string

    def _handle_children_output_suppressed_leaves(
        self,
        with_description: bool,
        depth_info: DepthInfo,
        child_depth_info: DepthInfo,
    ) -> Optional[str]:
        string = ""
        children_which_are_not_leaves = []
        some_children_which_are_leaves = False
        # The children need to be sorted first: Children which are not leaves come first.
        for child in self.children.values():
            if child.is_leaf():
                some_children_which_are_leaves = True
                continue
            children_which_are_not_leaves.append(child.name)
        if not some_children_which_are_leaves:
            return None
        for child in children_which_are_not_leaves:
            string += self.children[child].__str_for_depth(
                with_description, child_depth_info
            )
        CmdTreeNode._this_is_the_last_child(child_depth_info, depth_info)
        string += CmdTreeNode._create_supressed_children_line(
            child_depth_info, "leaves are hidden"
        )
        return string

    @staticmethod
    def _this_is_the_last_child(child_depth_info: DepthInfo, depth_info: DepthInfo):
        child_depth_info.last_child = True
        child_depth_info.set_layer_is_last_child(depth_info.depth)

    @staticmethod
    def _create_supressed_children_line(
        child_depth_info: DepthInfo, reason: str
    ) -> str:
        line = CmdTreeNode._create_leading_tree_part(child_depth_info)
        line += f"... (cut-off, {reason}){os.linesep}"
        return line

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
