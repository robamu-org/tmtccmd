#!/usr/bin/env python3
from __future__ import annotations
import typing
from PyQt6.QtCore import QModelIndex, QObject
from PyQt6.QtGui import QStandardItemModel


class TreeModel(QStandardItemModel):
    def __init__(self, parent: typing.Optional[QObject]):
        super().__init__(parent)
        pass

    def index(self, row: int, column: int, _: QModelIndex) -> QModelIndex:
        return self.createIndex(row, column, self)

    def parent(self, child: QModelIndex) -> QModelIndex:
        pass


def main():
    pass


if __name__ == "__main__":
    main()
