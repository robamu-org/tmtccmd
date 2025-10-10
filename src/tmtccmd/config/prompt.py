from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable

import prompt_toolkit
from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    WordCompleter,
)
from prompt_toolkit.completion.nested import NestedDict
from prompt_toolkit.document import Document
from prompt_toolkit.history import History
from prompt_toolkit.shortcuts import CompleteStyle

from tmtccmd.config.tmtc import CmdTreeNode

_LOGGER = logging.getLogger(__name__)


# TODO: There is an existing PR to merge this into prompt-toolkit.
# Delete this and use the package class as soon as https://github.com/prompt-toolkit/python-prompt-toolkit/pull/1815
# was merged and a new version was released.
class NestedCompleter(Completer):
    """
    Completer which wraps around several other completers, and calls any the
    one that corresponds with the first word of the input.

    By combining multiple `NestedCompleter` instances, we can achieve multiple
    hierarchical levels of autocompletion. This is useful when `WordCompleter`
    is not sufficient. The separator to trigger completion on the previously
    typed word is the Space character by default, but it is also possible
    to set a custom separator.

    If you need multiple levels, check out the `from_nested_dict` classmethod.
    """

    def __init__(
        self,
        options: dict[str, Completer | None],
        ignore_case: bool = True,
        separator: str = " ",
    ) -> None:
        self.options = options
        self.ignore_case = ignore_case
        self.separator = separator

    def __repr__(self) -> str:
        return (
            f"NestedCompleter({self.options!r}, ignore_case={self.ignore_case!r}, "
            f"separator={self.separator!r})"
        )

    @classmethod
    def from_nested_dict(
        cls, data: NestedDict, ignore_case: bool = True, separator: str = " "
    ) -> NestedCompleter:
        """
        Create a `NestedCompleter`, starting from a nested dictionary data
        structure, like this:

        .. code::

            data = {
                'show': {
                    'version': None,
                    'interfaces': None,
                    'clock': None,
                    'ip': {'interface': {'brief'}}
                },
                'exit': None
                'enable': None
            }

        The value should be `None` if there is no further completion at some
        point. If all values in the dictionary are None, it is also possible to
        use a set instead.

        Values in this data structure can be a completers as well.
        """
        options: dict[str, Completer | None] = {}
        for key, value in data.items():
            if isinstance(value, Completer):
                options[key] = value
            elif isinstance(value, dict):
                options[key] = cls.from_nested_dict(
                    data=value, ignore_case=ignore_case, separator=separator
                )
            elif isinstance(value, set):
                options[key] = cls.from_nested_dict(
                    data={item: None for item in value},
                    ignore_case=ignore_case,
                    separator=separator,
                )
            else:
                assert value is None
                options[key] = None

        return cls(options=options, ignore_case=ignore_case, separator=separator)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # Split document.
        text = document.text_before_cursor.lstrip(self.separator)
        stripped_len = len(document.text_before_cursor) - len(text)

        # If there is a separator character, check for the first term, and use a
        # subcompleter.
        if self.separator in text:
            first_term = text.split(self.separator)[0]
            completer = self.options.get(first_term)

            # If we have a sub completer, use this for the completions.
            if completer is not None:
                remaining_text = text[len(first_term) :].lstrip(self.separator)
                move_cursor = len(text) - len(remaining_text) + stripped_len

                new_document = Document(
                    remaining_text,
                    cursor_position=document.cursor_position - move_cursor,
                )

                yield from completer.get_completions(new_document, complete_event)

        # No space in the input: behave exactly like `WordCompleter`.
        else:
            completer = WordCompleter(list(self.options.keys()), ignore_case=self.ignore_case)
            yield from completer.get_completions(document, complete_event)


def prompt_cmd_path(
    cmd_def_tree: CmdTreeNode,
    history: History | None = None,
    compl_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
) -> str:
    compl_dict = cmd_def_tree.name_dict
    compl_dict = compl_dict.get("/")
    if compl_dict is None:
        return "/"
    nested_completer = NestedCompleter.from_nested_dict(compl_dict, separator="/")
    help_txt = (
        f"Additional commands for prompt:{os.linesep}"
        f":p[b][f][<depth>] Tree Print | :r Retry | :h Help Text | :c Cancel {os.linesep}"
        f"Auto complete is available using Tab after typing the slash character.{os.linesep}"
        f"If a command history was passed, use arrow up to access it.{os.linesep}"
        f"You can also print a subtree by typing the path and appending :p[b][p][<depth>]."
        f"{os.linesep}The b option for printouts enables brief printouts without descriptions."
        f"{os.linesep}The p option for printouts overrides hide flags to display all hidden nodes."
        f"{os.linesep}"
    )
    print(help_txt)
    while True:
        path_or_cmd = prompt_toolkit.prompt(
            message="> ",
            history=history,
            completer=nested_completer,
            complete_style=compl_style,
        )
        if ":p" in path_or_cmd:
            list_of_patterns = path_or_cmd.split(":")
            tree_to_print = cmd_def_tree
            if cmd_def_tree.contains_path(list_of_patterns[0]):
                tree_to_print = cmd_def_tree.extract_subnode(list_of_patterns[0])
                # Should never happen.
                assert tree_to_print is not None
            with_descriptions = True
            depth = None
            show_hidden_elements = False
            pattern = r"p([a-zA-Z]*)(\d*)"
            matches = re.search(pattern, list_of_patterns[1])
            if matches:
                if "b" in matches.group(1):
                    with_descriptions = False
                if "f" in matches.group(1):
                    show_hidden_elements = True
                if matches.group(2).isdigit():
                    depth = int(matches.group(2))
            print(
                tree_to_print.str_for_tree(
                    with_description=with_descriptions,
                    max_depth=depth,
                    show_hidden_elements=show_hidden_elements,
                )
            )
            continue
        elif ":h" in path_or_cmd:
            print(help_txt)
            continue
        elif ":r" in path_or_cmd:
            continue
        elif ":c" in path_or_cmd:
            break
        if not cmd_def_tree.contains_path(f"/{path_or_cmd}"):
            yes_or_no = input(
                "Command definitions tree does not contain the path. Try again? [y/n]: "
            )
            if yes_or_no in ["y", "yes", "1"]:
                continue
        break
    return f"/{path_or_cmd}"
