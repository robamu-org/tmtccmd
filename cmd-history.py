#!/usr/bin/env python3
import os
import datetime
from typing import Optional
from collections.abc import Iterable
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, History


class RotatingFileHistory(History):
    """
    :class:`.History` class that stores all strings in a file but has a bounded number of stored
    commands. If that bound is reached, a certain number of old commands specified by a
    window parameter will be removed for the command history file.
    """

    def __init__(
        self, filename: str, max_old_cmds: int, bound_window: Optional[int] = None
    ) -> None:
        self.filename = filename
        self.max_old_cmds = max_old_cmds
        self.bound_window = bound_window
        if self.bound_window is None:
            self.bound_window = self.max_old_cmds / 5
        super().__init__()

    def load_history_strings(self) -> Iterable[str]:
        strings: list[str] = []
        lines: list[str] = []

        def add() -> None:
            if lines:
                # Join and drop trailing newline.
                string = "".join(lines)[:-1]

                strings.append(string)

        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                for line_bytes in f:
                    line = line_bytes.decode("utf-8", errors="replace")

                    if line.startswith("+"):
                        lines.append(line[1:])
                    else:
                        add()
                        lines = []

                add()

        # Reverse the order, because newest items have to go first.
        return reversed(strings)

    def store_string(self, string: str) -> None:
        # Save to file.
        with open(self.filename, "ab") as f:

            def write(t: str) -> None:
                f.write(t.encode("utf-8"))

            write("\n# %s\n" % datetime.datetime.now())
            for line in string.split("\n"):
                write("+%s\n" % line)


session = PromptSession(history=FileHistory(".myhistory"))

while True:
    session.prompt()
