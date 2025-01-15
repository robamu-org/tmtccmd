from typing import List
from collections import deque
from PyQt6.QtCore import QModelIndex, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from tmtccmd.config.tmtc import CmdTreeNode


class CommandPathSelectWidget(QWidget):
    NODE_NAME_COLUMN = 0
    DESCRIPTION_COLUMN = 1

    path_selected_sig = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, root_node: CmdTreeNode, last_selected_items: deque):
        super().__init__()
        self.num_of_display_last_sel_items = 10
        self.last_selected_items = last_selected_items
        self.root_node = root_node
        self.currently_selected_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Command path selector")

        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Node Name", "Description"])
        parent_item = self.tree_model.invisibleRootItem()
        assert parent_item is not None
        CommandPathSelectWidget.build_tree_model_recursively(parent_item, self.root_node)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.expanded.connect(self._on_item_expanded)
        self.tree_view.doubleClicked.connect(self._on_tree_view_double_click)

        self.expand_full_button = QPushButton("Expand All")
        self.expand_full_button.clicked.connect(self.expand_all_items)

        self.fold_all_button = QPushButton("Fold All")
        self.fold_all_button.clicked.connect(self.collapse_all_items)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.expand_full_button)
        button_layout.addWidget(self.fold_all_button)

        self.last_sel_items_button = QPushButton("Last Selected Items")
        self.last_sel_items_button.clicked.connect(self._last_sel_items_clicked)
        self.select_path_button = QPushButton("Select Current Path")
        self.select_path_button.clicked.connect(self._select_path_clicked)
        self.copy_path_button = QPushButton("Copy Current Path to Clipboard")
        self.copy_path_button.clicked.connect(self._copy_path_clicked)
        self.path_confirmed_button = QPushButton("Confirm Selected Path")
        self.path_confirmed_button.clicked.connect(self._path_confirmed_clicked)

        self.path_label = QLabel()

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.tree_view)

        layout.addWidget(self.last_sel_items_button)
        layout.addWidget(self.select_path_button)
        layout.addWidget(self.copy_path_button)
        layout.addWidget(self.path_label)
        layout.addWidget(self.path_confirmed_button)
        self.setLayout(layout)

    def expand_all_items(self):
        self.tree_view.expandAll()

    def collapse_all_items(self):
        self.tree_view.collapseAll()

    def _last_sel_items_clicked(self):
        self.last_sel_cmds_widget = QListWidget()
        self.last_sel_cmds_widget.setWindowTitle("Last selected items")
        for item in self.last_selected_items:
            self.last_sel_cmds_widget.addItem(QListWidgetItem(item))
        self.last_sel_cmds_widget.doubleClicked.connect(self._last_sel_item_confirmed)
        self.last_sel_cmds_widget.show()

    def _path_confirmed_clicked(self):
        if self.currently_selected_path is None:
            # TODO: Error handling in some shape or form, maybe message box?
            return
        self.path_selected_sig.emit(self.currently_selected_path)
        if len(self.last_selected_items) >= self.num_of_display_last_sel_items:
            self.last_selected_items.popleft()
        self.last_selected_items.append(self.currently_selected_path)
        self.closed.emit()
        self.close()

    @staticmethod
    def build_tree_model_recursively(current_item: QStandardItem, current_node: CmdTreeNode):
        for child in current_node.children.values():
            new_item = QStandardItem(child.name)
            current_item.appendRow([new_item, QStandardItem(child.description)])
            if child.children:
                CommandPathSelectWidget.build_tree_model_recursively(new_item, child)

    def _on_tree_view_double_click(self, _index: int):
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            index = selected_indexes[0]  # Get the first selected index
            item = self.tree_model.itemFromIndex(index)
            assert item is not None
            if not item.hasChildren():
                self._select_path_clicked_by_index(selected_indexes)
            else:
                self.tree_view.expand(selected_indexes[0])
        self._path_confirmed_clicked()

    def _on_item_expanded(self, _index: int):
        self.tree_view.resizeColumnToContents(CommandPathSelectWidget.NODE_NAME_COLUMN)
        self.tree_view.resizeColumnToContents(CommandPathSelectWidget.DESCRIPTION_COLUMN)
        self.resize(
            self.tree_view.sizeHintForColumn(CommandPathSelectWidget.NODE_NAME_COLUMN)
            + self.tree_view.sizeHintForColumn(CommandPathSelectWidget.DESCRIPTION_COLUMN)
            + 40,
            self.size().height(),
        )

    def _select_path_clicked(self):
        self._select_path_clicked_by_index(self.tree_view.selectedIndexes())

    def _select_path_clicked_by_index(self, selected_indexes: List[QModelIndex]):
        if selected_indexes:
            index = selected_indexes[0]  # Get the first selected index
            item = self.tree_model.itemFromIndex(index)
            self._update_sel_path_common(f"/{self._get_item_path(item)}")

    def _last_sel_item_confirmed(self, item: QModelIndex):
        self._update_sel_path_common(self.last_selected_items[item.row()])
        self.last_sel_cmds_widget.close()

    def _update_sel_path_common(self, path: str):
        self.currently_selected_path = path
        self.path_label.setText(f"Selected: {self.currently_selected_path}")

    def _copy_path_clicked(self):
        if self.currently_selected_path is None:
            self._select_path_clicked()
        if self.currently_selected_path is not None:
            print(f"Copied path {self.currently_selected_path} to clipboard.")
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self.currently_selected_path)

    def _get_item_path(self, item):
        path = []
        while item:
            path.insert(0, item.text())
            item = item.parent()
        return "/".join(path)
