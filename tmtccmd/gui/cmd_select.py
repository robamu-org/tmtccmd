from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
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

    def __init__(self, root_node: CmdTreeNode):
        super().__init__()
        self.root_node = root_node
        self.currently_selected_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Command path selector")

        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Node Name", "Description"])
        parent_item = self.tree_model.invisibleRootItem()
        assert parent_item is not None
        CommandPathSelectWidget.build_tree_model_recursively(
            parent_item, self.root_node
        )

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self.tree_view.expanded.connect(self.on_item_expanded)

        self.expand_full_button = QPushButton("Expand All")
        self.expand_full_button.clicked.connect(self.expand_all_items)

        self.fold_all_button = QPushButton("Fold All")
        self.fold_all_button.clicked.connect(self.collapse_all_items)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.expand_full_button)
        button_layout.addWidget(self.fold_all_button)

        self.select_path_button = QPushButton("Select Current Path")
        self.select_path_button.clicked.connect(self.select_path_clicked)
        self.copy_path_button = QPushButton("Copy Current Path to Clipboard")
        self.copy_path_button.clicked.connect(self.copy_path_clicked)
        self.path_confirmed_button = QPushButton("Confirm Selected Path")
        self.path_confirmed_button.clicked.connect(self.path_confirmed_clicked)

        self.path_label = QLabel()

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.tree_view)
        layout.addWidget(self.select_path_button)
        layout.addWidget(self.copy_path_button)
        layout.addWidget(self.path_label)
        layout.addWidget(self.path_confirmed_button)
        self.setLayout(layout)

    def expand_all_items(self):
        self.tree_view.expandAll()

    def collapse_all_items(self):
        self.tree_view.collapseAll()

    def path_confirmed_clicked(self):
        if self.currently_selected_path is None:
            # TODO: Error handling in some shape or form, maybe message box?
            return
        self.path_selected_sig.emit(self.currently_selected_path)
        self.closed.emit()
        self.close()

    @staticmethod
    def build_tree_model_recursively(
        current_item: QStandardItem, current_node: CmdTreeNode
    ):
        for child in current_node.children.values():
            new_item = QStandardItem(child.name)
            current_item.appendRow([new_item, QStandardItem(child.description)])
            if child.children:
                CommandPathSelectWidget.build_tree_model_recursively(new_item, child)

    def on_item_expanded(self, _index: int):
        self.tree_view.resizeColumnToContents(CommandPathSelectWidget.NODE_NAME_COLUMN)
        self.tree_view.resizeColumnToContents(
            CommandPathSelectWidget.DESCRIPTION_COLUMN
        )
        self.resize(
            self.tree_view.sizeHintForColumn(CommandPathSelectWidget.NODE_NAME_COLUMN)
            + self.tree_view.sizeHintForColumn(
                CommandPathSelectWidget.DESCRIPTION_COLUMN
            )
            + 40,
            self.size().height(),
        )

    def select_path_clicked(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            index = selected_indexes[0]  # Get the first selected index
            item = self.tree_model.itemFromIndex(index)
            self.currently_selected_path = f"/{self.get_item_path(item)}"
            self.path_label.setText(f"Selected: {self.currently_selected_path}")

    def copy_path_clicked(self):
        if self.currently_selected_path is None:
            self.select_path_clicked()
        if self.currently_selected_path is not None:
            print(f"Copied path {self.currently_selected_path} to clipboard.")
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self.currently_selected_path)

    def get_item_path(self, item):
        path = []
        while item:
            path.insert(0, item.text())
            item = item.parent()
        return "/".join(path)
