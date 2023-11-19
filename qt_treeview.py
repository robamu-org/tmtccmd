#!/usr/bin/env python3
from __future__ import annotations
import sys
import signal

from PyQt6.QtCore import QTimer, pyqtSignal
from tmtccmd.config.tmtc import CmdTreeNode
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTreeView,
    QApplication,
    QVBoxLayout,
    QWidget,
)


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

    def select_path_clicked(self):
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            index = selected_indexes[0]  # Get the first selected index
            item = self.tree_model.itemFromIndex(index)
            self.currently_selected_path = self.get_item_path(item)
            self.path_label.setText(f"Selected: {self.currently_selected_path}")

    def copy_path_clicked(self):
        if self.currently_selected_path is None:
            self.select_path_clicked()
        if self.currently_selected_path is not None:
            print(f"Copied path {self.currently_selected_path} to clipboard.")
            QApplication.clipboard().setText(self.currently_selected_path)

    def get_item_path(self, item):
        path = []
        while item:
            path.insert(0, item.text())
            item = item.parent()
        return "/".join(path)


class MainWindow(QMainWindow):
    def __init__(self, root_node: CmdTreeNode):
        super().__init__()
        self.root_node = root_node
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Main Application")
        self.cmd_select_window = None

        self.open_command_path_select_button = QPushButton("Open Command Path Selector")
        self.open_command_path_select_button.clicked.connect(
            self.open_command_select_widget
        )
        self.setCentralWidget(self.open_command_path_select_button)

    def open_command_select_widget(self):
        self.cmd_select_window = CommandPathSelectWidget(self.root_node)
        self.cmd_select_window.path_selected_sig.connect(self.receive_selected_path)
        self.cmd_select_window.closed.connect(self.on_treeview_closed)
        self.cmd_select_window.show()
        self.open_command_path_select_button.setEnabled(False)

    def on_treeview_closed(self):
        if self.cmd_select_window is not None:
            self.open_command_path_select_button.setEnabled(True)

    def receive_selected_path(self, path):
        QMessageBox.information(self, "Selected Path", f"Selected Path: {path}")


def sigint_handler(_sig, _frame):
    QApplication.quit()


def main():
    app = QApplication(sys.argv)

    # Let the interpreter run some time to also catch SIGINTs.
    timer = QTimer()
    timer.start(500)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    # Connect Ctrl + C signal to the handler
    signal.signal(signal.SIGINT, sigint_handler)

    root_node = CmdTreeNode.root_node()
    root_node.add_child(CmdTreeNode("acs", "ACS Subsystem"))
    root_node.children["acs"].add_child(CmdTreeNode("acs_ctrl", "ACS Controller"))
    root_node.children["acs"].children["acs_ctrl"].add_child(
        CmdTreeNode("set_param", "Set Parameter")
    )
    root_node.add_child(CmdTreeNode("tcs", "TCS Subsystem"))
    root_node.children["tcs"].add_child(CmdTreeNode("tcs_ctrl", "TCS Controller"))

    main_widget = MainWindow(root_node)
    main_widget.show()
    app.exec()


if __name__ == "__main__":
    main()
