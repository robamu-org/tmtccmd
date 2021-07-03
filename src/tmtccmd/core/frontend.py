#!/usr/bin/env python3
"""
@file           tmtc_frontend.py
@date           01.11.2019
@brief          This is part of the TMTC client developed by the SOURCE project by KSat
@description    GUI is still work-in-progress
@manual
@author         R. Mueller, P. Scheurenbrand, D. Nguyen
"""
import enum
import os
import sys
import time
import webbrowser
from multiprocessing import Process
from typing import Union

from PyQt5.QtWidgets import QMainWindow, QGridLayout, QTableWidget, QWidget, QLabel, QCheckBox, \
    QDoubleSpinBox, QFrame, QComboBox, QPushButton, QTableWidgetItem, QMenu, QAction, QMenuBar
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QRunnable

from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.config.definitions import CoreGlobalIds, CoreModeList, CoreComInterfaces
from tmtccmd.config.hook import get_global_hook_obj
from tmtccmd.utility.logger import get_console_logger
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.tcpip_utilities import TcpIpConfigIds
import tmtccmd.config as config_module


LOGGER = get_console_logger()


CONNECT_BTTN_STYLE = \
    "background-color: #1fc600;" \
    "border-style: inset;" \
    "font: bold;" \
    "padding: 6px;" \
    "border-width: 2px;" \
    "border-radius: 6px;"


DISCONNECT_BTTN_STYLE = \
    "background-color: orange;" \
    "border-style: inset;" \
    "font: bold;" \
    "padding: 6px;" \
    "border-width: 2px;" \
    "border-radius: 6px;"


COMMAND_BUTTON_STYLE = \
    "background-color: #cdeefd;" \
    "border-style: inset;" \
    "font: bold;" \
    "padding: 6px;" \
    "border-width: 2px;" \
    "border-radius: 6px;"


class WorkerOperationsCodes(enum.IntEnum):
    DISCONNECT = 0
    SEQUENTIAL_COMMANDING = 1


class WorkerThread(QObject):
    finished = pyqtSignal()

    def __init__(self, op_code: WorkerOperationsCodes, tmtc_handler: TmTcHandler):
        super(QObject, self).__init__()
        self.op_code = op_code
        self.tmtc_handler = tmtc_handler

    def run_worker(self):
        if self.op_code == WorkerOperationsCodes.DISCONNECT:
            self.tmtc_handler.close_listener()
            while True:
                if not self.tmtc_handler.is_com_if_active():
                    break
                else:
                    time.sleep(0.4)
            self.finished.emit()
        elif self.op_code == WorkerOperationsCodes.SEQUENTIAL_COMMANDING:
            self.tmtc_handler.set_mode(CoreModeList.SEQUENTIAL_CMD_MODE)
            # It is expected that the TMTC handler is in the according state to perform the operation
            self.tmtc_handler.perform_operation()
            self.finished.emit()
        else:
            LOGGER.warning("Unknown worker operation code!")
            self.finished.emit()


class RunnableThread(QRunnable):
    """
    Runnable thread which can be used with QThreadPool. Not used for now, might be needed in the future.
    """
    def run(self):
        pass


class TmTcFrontend(QMainWindow, FrontendBase):
    def __init__(self, hook_obj: TmTcHookBase, tmtc_backend: TmTcHandler, app_name: str):
        super(TmTcFrontend, self).__init__()
        super(QMainWindow, self).__init__()
        self._tmtc_handler = tmtc_backend
        self._app_name = app_name
        self._hook_obj = hook_obj

        self._tmtc_handler.initialize()
        self.service_op_code_dict = dict()
        self._service_list = []
        self._op_code_list = []
        self._com_if_list = []
        self._last_com_if = CoreComInterfaces.UNSPECIFIED.value
        self._current_com_if = CoreComInterfaces.UNSPECIFIED.value
        self._current_service = ""
        self._current_op_code = ""
        self._current_com_if_key = "unspec"
        self.__connected = False

        self.__worker = None
        self.__thread = None
        self.__debug_mode = False

        self.__combo_box_op_codes: Union[None, QComboBox] = None
        module_path = os.path.abspath(config_module.__file__).replace("__init__.py", "")
        self.logo_path = f"{module_path}/logo.png"

    def prepare_start(self, args: any) -> Process:
        return Process(target=self.start)

    def start(self, qt_app: any):
        self.__start_ui()
        sys.exit(qt_app.exec())

    def set_gui_logo(self, logo_total_path: str):
        if os.path.isfile(logo_total_path):
            self.logo_path = logo_total_path
        else:
            LOGGER.warning("Could not set logo, path invalid!")

    def __start_ui(self):
        self.__create_menu_bar()
        win = QWidget(self)
        self.setCentralWidget(win)

        grid = QGridLayout()
        win.setLayout(grid)
        row = 0
        self.setWindowTitle(self._app_name)
        self.setWindowIcon(QIcon(self.logo_path))

        add_pixmap = False

        if add_pixmap:
            row = self.__set_up_pixmap(grid=grid, row=row)

        row = self.__set_up_config_section(grid=grid, row=row)
        row = self.__add_vertical_separator(grid=grid, row=row)

        # com if configuration
        row = self.__set_up_com_if_section(grid=grid, row=row)
        row = self.__add_vertical_separator(grid=grid, row=row)

        row = self.__set_up_service_op_code_section(grid=grid, row=row)

        self.__command_button = QPushButton()
        self.__command_button.setText("Send Command")
        self.__command_button.setStyleSheet(
            COMMAND_BUTTON_STYLE
        )
        self.__command_button.clicked.connect(self.__start_seq_cmd_op)
        self.__command_button.setEnabled(False)
        grid.addWidget(self.__command_button, row, 0, 1, 2)
        row += 1
        self.show()

    def __start_seq_cmd_op(self):
        if self.__debug_mode:
            LOGGER.info("Start Service Test Button pressed.")
        if not self.__get_send_button():
            return
        self.__set_send_button(False)
        self._tmtc_handler.set_service(self._current_service)
        self._tmtc_handler.set_opcode(self._current_op_code)
        self.__start_qthread_task(
            op_code=WorkerOperationsCodes.SEQUENTIAL_COMMANDING, finish_callback=self.__finish_seq_cmd_op
        )

    def __finish_seq_cmd_op(self):
        self.__set_send_button(True)

    def __connect_button_action(self):
        if not self.__connected:
            LOGGER.info("Starting TM listener..")
            # Build and assign new communication interface
            if self._current_com_if != self._last_com_if:
                hook_obj = get_global_hook_obj()
                new_com_if = hook_obj.assign_communication_interface(
                    com_if_key=self._current_com_if, tmtc_printer=self._tmtc_handler.get_printer()
                )
                self._tmtc_handler.set_com_if(new_com_if)
            self._tmtc_handler.start_listener(False)
            self.__connect_button.setStyleSheet(
                DISCONNECT_BTTN_STYLE
            )
            self.__command_button.setEnabled(True)
            self.__connect_button.setText("Disconnect")
            self.__connected = True
        else:
            LOGGER.info("Closing TM listener..")
            self.__command_button.setEnabled(False)
            self.__connect_button.setEnabled(False)
            self.__start_qthread_task(
                op_code=WorkerOperationsCodes.DISCONNECT, finish_callback=self.__finish_disconnect_button_op
            )

    def __finish_disconnect_button_op(self):
        self.__connect_button.setEnabled(True)
        # self.__disconnect_button.setEnabled(False)
        self.__connect_button.setStyleSheet(
            CONNECT_BTTN_STYLE
        )
        self.__connect_button.setText("Connect")
        LOGGER.info("Disconnect successfull")
        self.__connected = False

    def __create_menu_bar(self):
        menu_bar = self.menuBar()
        # Creating menus using a QMenu object
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        # Creating menus using a title
        help_menu = menu_bar.addMenu("&Help")

        help_action = QAction("Help", self)
        help_action.triggered.connect(self.__help_url)
        help_menu.addAction(help_action)

    @staticmethod
    def __help_url():
        webbrowser.open('https://tmtccmd.readthedocs.io/en/latest/')

    def __set_up_config_section(self, grid: QGridLayout, row: int) -> int:
        grid.addWidget(QLabel("Configuration:"), row, 0, 1, 2)
        row += 1
        checkbox_console = QCheckBox("Print output to console")
        checkbox_console.stateChanged.connect(self.__checkbox_console_update)

        checkbox_log = QCheckBox("Print output to log file")
        checkbox_log.stateChanged.connect(self.__checkbox_log_update)

        checkbox_raw_tm = QCheckBox("Print all raw TM data directly")
        checkbox_raw_tm.stateChanged.connect(self.__checkbox_print_raw_data_update)

        checkbox_hk = QCheckBox("Print Housekeeping Data")
        # checkbox_hk.setChecked(tmtcc_config.G_PRINT_HK_DATA)
        checkbox_hk.stateChanged.connect(checkbox_print_hk_data)

        checkbox_short = QCheckBox("Short Display Mode")
        # checkbox_short.setChecked(tmtcc_config.G_DISPLAY_MODE == "short")
        checkbox_short.stateChanged.connect(checkbox_short_display_mode)

        grid.addWidget(checkbox_log, row, 0, 1, 1)
        grid.addWidget(checkbox_console, row, 1, 1, 1)
        row += 1
        grid.addWidget(checkbox_raw_tm, row, 0, 1, 1)
        grid.addWidget(checkbox_hk, row, 1, 1, 1)
        row += 1
        grid.addWidget(checkbox_short, row, 0, 1, 1)
        row += 1

        grid.addWidget(QLabel("TM Timeout:"), row, 0, 1, 1)
        grid.addWidget(QLabel("TM Timeout Factor:"), row, 1, 1, 1)
        row += 1

        spin_timeout = QDoubleSpinBox()
        spin_timeout.setValue(4)
        # TODO: set sensible min/max values
        spin_timeout.setSingleStep(0.1)
        spin_timeout.setMinimum(0.25)
        spin_timeout.setMaximum(60)
        # https://youtrack.jetbrains.com/issue/PY-22908
        # Ignore those warnings for now.
        spin_timeout.valueChanged.connect(number_timeout)
        grid.addWidget(spin_timeout, row, 0, 1, 1)

        spin_timeout_factor = QDoubleSpinBox()
        # spin_timeout_factor.setValue(tmtcc_config.G_TC_SEND_TIMEOUT_FACTOR)
        # TODO: set sensible min/max values
        spin_timeout_factor.setSingleStep(0.1)
        spin_timeout_factor.setMinimum(0.25)
        spin_timeout_factor.setMaximum(10)
        spin_timeout_factor.valueChanged.connect(number_timeout_factor)
        grid.addWidget(spin_timeout_factor, row, 1, 1, 1)
        row += 1
        return row

    def __set_up_com_if_section(self, grid: QGridLayout, row: int) -> int:
        grid.addWidget(QLabel("Communication Interface:"), row, 0, 1, 1)
        com_if_combo_box = QComboBox()
        all_com_ifs = get_global(CoreGlobalIds.COM_IF_DICT)
        index = 0
        # add all possible ComIFs to the comboBox
        for com_if_key, com_if_value in all_com_ifs.items():
            com_if_combo_box.addItem(com_if_value)
            self._com_if_list.append((com_if_key, com_if_value))
            if self._tmtc_handler.get_com_if_id() == com_if_key:
                com_if_combo_box.setCurrentIndex(index)
            index += 1
        com_if_combo_box.currentIndexChanged.connect(self.__com_if_index_changed)
        grid.addWidget(com_if_combo_box, row, 1, 1, 1)
        row += 1

        self.com_if_cfg_button = QPushButton()
        self.com_if_cfg_button.setText("Configure")
        grid.addWidget(self.com_if_cfg_button, row, 0, 1, 2)
        row += 1

        self.__connect_button = QPushButton()
        self.__connect_button.setText("Connect")
        self.__connect_button.setStyleSheet(
            CONNECT_BTTN_STYLE
        )
        self.__connect_button.clicked.connect(self.__connect_button_action)

        grid.addWidget(self.__connect_button, row, 0, 1, 2)
        row += 1
        return row

    def __set_up_service_op_code_section(self, grid: QGridLayout, row: int):
        grid.addWidget(QLabel("Service: "), row, 0, 1, 2)
        grid.addWidget(QLabel("Operation Code: "), row, 1, 1, 2)
        row += 1

        combo_box_services = QComboBox()
        default_service = get_global(CoreGlobalIds.CURRENT_SERVICE)
        self.service_op_code_dict = self._hook_obj.get_service_op_code_dictionary()
        if self.service_op_code_dict is None:
            LOGGER.warning("Invalid service to operation code dictionary")
            LOGGER.warning("Setting default dictionary")
            from tmtccmd.config.globals import get_default_service_op_code_dict
            self.service_op_code_dict = get_default_service_op_code_dict()
        index = 0
        default_index = 0
        for service_key, service_value in self.service_op_code_dict.items():
            combo_box_services.addItem(service_value[0])
            if service_key == default_service:
                default_index = index
            self._service_list.append(service_key)
            index += 1
        combo_box_services.setCurrentIndex(default_index)
        self._current_service = self._service_list[default_index]

        combo_box_services.currentIndexChanged.connect(self.__service_index_changed)
        grid.addWidget(combo_box_services, row, 0, 1, 1)

        self.__combo_box_op_codes = QComboBox()
        self._current_service = self._service_list[default_index]
        self.__update_op_code_combo_box()
        self.__combo_box_op_codes.currentIndexChanged.connect(self.__op_code_index_changed)
        # TODO: Combo box also needs to be updated if another service is selected
        grid.addWidget(self.__combo_box_op_codes, row, 1, 1, 1)
        row += 1
        return row

    def __set_up_pixmap(self, grid: QGridLayout, row: int) -> int:
        label = QLabel(self)
        label.setGeometry(720, 10, 100, 100)
        label.adjustSize()

        pixmap = QPixmap(self.logo_path)
        pixmap_width = pixmap.width()
        pixmap_height = pixmap.height()
        row += 1

        pixmap_scaled = pixmap.scaled(pixmap_width * 0.3, pixmap_height * 0.3, Qt.KeepAspectRatio)
        label.setPixmap(pixmap_scaled)
        label.setScaledContents(True)

        grid.addWidget(label, row, 0, 1, 2)
        row += 1
        return row

    def __start_qthread_task(self, op_code: WorkerOperationsCodes, finish_callback):
        self.__thread = QThread()
        self.__worker = WorkerThread(
            op_code=op_code, tmtc_handler=self._tmtc_handler
        )
        self.__worker.moveToThread(self.__thread)

        self.__thread.started.connect(self.__worker.run_worker)
        self.__worker.finished.connect(self.__thread.quit)
        self.__worker.finished.connect(self.__worker.deleteLater)
        self.__thread.finished.connect(self.__thread.deleteLater)

        self.__thread.finished.connect(finish_callback)
        self.__thread.start()

    @staticmethod
    def __add_vertical_separator(grid: QGridLayout, row: int):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        grid.addWidget(separator, row, 0, 1, 2)
        row += 1
        return row

    def __service_index_changed(self, index: int):
        self._current_service = self._service_list[index]
        self.__update_op_code_combo_box()
        if self.__debug_mode:
            LOGGER.info("Service changed")

    def __op_code_index_changed(self, index: int):
        self._current_op_code = self._op_code_list[index]
        if self.__debug_mode:
            LOGGER.info("Op Code changed")

    def __update_op_code_combo_box(self):
        self.__combo_box_op_codes.clear()
        self._op_code_list = []
        op_code_dict = self.service_op_code_dict[self._current_service][1]
        if op_code_dict is not None:
            for op_code_key, op_code_value in op_code_dict.items():
                self._op_code_list.append(op_code_key)
                self.__combo_box_op_codes.addItem(op_code_value[0])
            self._current_op_code = self._op_code_list[0]

    def __checkbox_log_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_TO_FILE, state)
        if self.__debug_mode:
            LOGGER.info(["Enabled", "Disabled"][state == 0] + " print to log.")

    def __checkbox_console_update(self, state: bool):
        update_global(CoreGlobalIds.PRINT_TM, state)
        if self.__debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " console print")

    def __checkbox_print_raw_data_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_RAW_TM, state)
        if self.__debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " printing of raw data")

    def __set_send_button(self, state: bool):
        self.__command_button.setEnabled(state)

    def __get_send_button(self):
        return self.__command_button.isEnabled()

    def __com_if_index_changed(self, index: int):
        self._current_com_if = self._com_if_list[index][0]
        if self.__debug_mode:
            LOGGER.info(f"Communication IF updated: {self._com_if_list[index][1]}")


class SingleCommandTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setRowCount(1)
        self.setColumnCount(5)
        self.setHorizontalHeaderItem(0, QTableWidgetItem("Service"))
        self.setHorizontalHeaderItem(1, QTableWidgetItem("Subservice"))
        self.setHorizontalHeaderItem(2, QTableWidgetItem("SSC"))
        self.setHorizontalHeaderItem(3, QTableWidgetItem("Data"))
        self.setHorizontalHeaderItem(4, QTableWidgetItem("CRC"))
        self.setItem(0, 0, QTableWidgetItem("17"))
        self.setItem(0, 1, QTableWidgetItem("1"))
        self.setItem(0, 2, QTableWidgetItem("20"))


def checkbox_print_hk_data(state: int):
    update_global(CoreGlobalIds.PRINT_HK, state)
    LOGGER.info(["enabled", "disabled"][state == 0] + " printing of hk data")


def checkbox_short_display_mode(state: int):
    update_global(CoreGlobalIds.DISPLAY_MODE, state)
    LOGGER.info(["enabled", "disabled"][state == 0] + " short display mode")


def number_timeout(value: float):
    update_global(CoreGlobalIds.TM_TIMEOUT, value)
    LOGGER.info("PUS TM timeout changed to: " + str(value))


def number_timeout_factor(value: float):
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, value)
    LOGGER.info("PUS TM timeout factor changed to: " + str(value))


def ip_change_client(value):
    ethernet_config = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_config[TcpIpConfigIds.RECV_ADDRESS] = value
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_config)
    LOGGER.info("Client IP changed: " + value)


def ip_change_board(value):
    ethernet_config = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_config[TcpIpConfigIds.SEND_ADDRESS] = value
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_config)
    LOGGER.info("Board IP changed: " + value)
