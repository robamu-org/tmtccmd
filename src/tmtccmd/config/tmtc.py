from __future__ import annotations

import copy
import enum
import os
from typing import Any


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
        max_depth: int | None = None,
        layer_is_last_set: set[int] | None = None,
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
        parent: CmdTreeNode | None = None,
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
        self.parent: CmdTreeNode | None = parent
        self.children: dict[str, CmdTreeNode] = {}
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

    def contains_path_from_node_list(self, node_name_list: list[str]) -> bool:
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

    def extract_subnode(self, path: str) -> CmdTreeNode | None:
        """Extract a subnode given a relative path."""
        if path == "":
            return None
        return self.extract_subnode_by_node_list(path.split("/"))

    def extract_subnode_by_node_list(self, node_list: list[str]) -> CmdTreeNode | None:
        """Extract a subnode given a list which would form a relative path if it were joined
        using slashes."""
        if not self.contains_path_from_node_list(node_list):
            return None
        if len(node_list) == 1 and self.children[node_list[0]] is not None:
            return self.children[node_list[0]]
        return self.children[node_list[0]].extract_subnode_by_node_list(node_list[1:])

    @property
    def name_dict(self) -> dict[str, dict[str, Any] | None]:
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
        max_depth: int | None = None,
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
        if not show_hidden_elements and self.hide_children_for_print and len(self.children) > 0:
            CmdTreeNode._this_is_the_last_child(child_depth_info, depth_info)
            string += CmdTreeNode._create_supressed_children_line(
                child_depth_info, "children are hidden"
            )
        else:
            if not show_hidden_elements and self.hide_children_which_are_leaves:
                str_if_there_are_leaves = self._handle_children_output_suppressed_leaves(
                    with_description, depth_info, child_depth_info
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
    ) -> str | None:
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
            string += self.children[child].__str_for_depth(with_description, child_depth_info)
        CmdTreeNode._this_is_the_last_child(child_depth_info, depth_info)
        string += CmdTreeNode._create_supressed_children_line(child_depth_info, "leaves are hidden")
        return string

    @staticmethod
    def _this_is_the_last_child(child_depth_info: DepthInfo, depth_info: DepthInfo):
        child_depth_info.last_child = True
        child_depth_info.set_layer_is_last_child(depth_info.depth)

    @staticmethod
    def _create_supressed_children_line(child_depth_info: DepthInfo, reason: str) -> str:
        line = CmdTreeNode._create_leading_tree_part(child_depth_info)
        line += f"... (cut-off, {reason}){os.linesep}"
        return line

    def __str__(self) -> str:
        return self.str_for_tree(False)
