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
import threading
import os
import sys
import time
from multiprocessing import Process

from PyQt5.QtWidgets import QMainWindow, QGridLayout, QTableWidget, QWidget, QLabel, QCheckBox, \
    QDoubleSpinBox, QFrame, QComboBox, QPushButton, QTableWidgetItem, QMenu
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThread, QRunnable

from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.config.hook import TmTcHookBase
from tmtccmd.config.definitions import CoreComInterfacesDict, CoreGlobalIds, CoreModeList, CoreComInterfaces
from tmtccmd.config.globals import get_global_apid
from tmtccmd.config.hook import get_global_hook_obj
from tmtccmd.pus_tc.definitions import PusTelecommand
from tmtccmd.utility.logger import get_logger
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.tcpip_utilities import TcpIpConfigIds
import tmtccmd.config as config_module


LOGGER = get_logger()


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
        self.tmtc_handler = tmtc_backend
        self.app_name = app_name
        self.hook_obj = hook_obj

        self.tmtc_handler.initialize()
        self.service_list = []
        self.op_code_list = []
        self.com_if_list = []
        self.last_com_if = CoreComInterfaces.UNSPECIFIED.value
        self.current_com_if = CoreComInterfaces.UNSPECIFIED.value
        self.current_service = ""
        self.current_op_code = ""
        self.current_com_if_id = -1

        self.worker = None
        self.thread = None
        self.debug_mode = True
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
        self.setWindowTitle(self.app_name)
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
        self.__command_button.clicked.connect(self.__start_seq_cmd_op)
        self.__command_button.setEnabled(False)
        grid.addWidget(self.__command_button, row, 0, 1, 2)
        row += 1

        self.show()

    def __start_seq_cmd_op(self):
        # TODO: Use worker thread instead here. We need the event loop because right now, the maximum number
        #       of concurrent send operations is one for now
        if self.debug_mode:
            LOGGER.info("Start Service Test Button pressed.")
        if not self.__get_send_button():
            return
        self.__set_send_button(False)
        # TODO: If it has change, we might need to disconnect from old one
        self.tmtc_handler.set_service(self.current_service)
        self.tmtc_handler.set_opcode(self.current_op_code)
        # TODO: Need to check whether COM IF has changed, build and reassign a new one it this is the case
        self.__start_qthread_task(
            op_code=WorkerOperationsCodes.SEQUENTIAL_COMMANDING, finish_callback=self.__finish_seq_cmd_op
        )

    def __finish_seq_cmd_op(self):
        self.__set_send_button(True)

    def __start_connect_button_action(self):
        LOGGER.info("Starting TM listener..")
        # Build and assign new communication interface
        if self.current_com_if != self.last_com_if:
            hook_obj = get_global_hook_obj()
            new_com_if = hook_obj.assign_communication_interface(
                com_if_key=self.current_com_if, tmtc_printer=self.tmtc_handler.get_printer()
            )
            self.tmtc_handler.set_com_if(new_com_if)
        self.tmtc_handler.start_listener(False)
        self.__connect_button.setStyleSheet("background-color: green")
        self.__connect_button.setEnabled(False)
        self.__disconnect_button.setEnabled(True)
        self.__command_button.setEnabled(True)
        self.__disconnect_button.setStyleSheet("background-color: orange")

    def __start_disconnect_button_op(self):
        LOGGER.info("Closing TM listener..")
        self.__disconnect_button.setEnabled(False)
        self.__command_button.setEnabled(False)
        if not self.__connect_button.isEnabled():
            self.__start_qthread_task(
                op_code=WorkerOperationsCodes.DISCONNECT, finish_callback=self.__finish_disconnect_button_op
            )

    def __finish_disconnect_button_op(self):
        self.__connect_button.setEnabled(True)
        self.__disconnect_button.setEnabled(False)
        self.__disconnect_button.setStyleSheet("background-color: red")
        self.__connect_button.setStyleSheet("background-color: lime")
        LOGGER.info("Disconnect successfull")

    def __create_menu_bar(self):
        menuBar = self.menuBar()
        # Creating menus using a QMenu object
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        # Creating menus using a title
        editMenu = menuBar.addMenu("&Edit")
        helpMenu = menuBar.addMenu("&Help")

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
            self.com_if_list.append((com_if_key, com_if_value))
            if self.tmtc_handler.get_com_if_id() == com_if_key:
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
        self.__connect_button.setStyleSheet("background-color: lime")
        self.__connect_button.pressed.connect(self.__start_connect_button_action)

        self.__disconnect_button = QPushButton()
        self.__disconnect_button.setText("Disconnect")
        self.__disconnect_button.setStyleSheet("background-color: orange")
        self.__disconnect_button.pressed.connect(self.__start_disconnect_button_op)
        self.__disconnect_button.setEnabled(False)

        grid.addWidget(self.__connect_button, row, 0, 1, 1)
        grid.addWidget(self.__disconnect_button, row, 1, 1, 1)
        row += 1
        return row

    def __set_up_service_op_code_section(self, grid: QGridLayout, row: int):
        # service test mode gui
        grid.addWidget(QLabel("Service: "), row, 0, 1, 2)
        grid.addWidget(QLabel("Operation Code: "), row, 1, 1, 2)
        row += 1

        combo_box_services = QComboBox()
        default_service = get_global(CoreGlobalIds.CURRENT_SERVICE)
        service_op_code_dict = self.hook_obj.get_service_op_code_dictionary()
        if service_op_code_dict is None:
            LOGGER.warning("Invalid service to operation code dictionary")
            LOGGER.warning("Setting default dictionary")
            from tmtccmd.config.globals import get_default_service_op_code_dict
            service_op_code_dict = get_default_service_op_code_dict()
        index = 0
        default_index = 0
        for service_key, service_value in service_op_code_dict.items():
            combo_box_services.addItem(service_value[0])
            if service_key == default_service:
                default_index = index
            self.service_list.append(service_key)
            index += 1
        combo_box_services.setCurrentIndex(default_index)
        self.current_service = self.service_list[default_index]

        combo_box_services.currentIndexChanged.connect(self.__service_index_changed)
        grid.addWidget(combo_box_services, row, 0, 1, 1)

        combo_box_op_codes = QComboBox()
        current_service = self.service_list[default_index]
        op_code_dict = service_op_code_dict[current_service][1]
        if op_code_dict is not None:
            for op_code_key, op_code_value in op_code_dict.items():
                self.op_code_list.append(op_code_key)
                combo_box_op_codes.addItem(op_code_value[0])
            self.current_op_code = self.op_code_list[0]
        # TODO: Combo box also needs to be updated if another service is selected
        grid.addWidget(combo_box_op_codes, row, 1, 1, 1)
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
        self.thread = QThread()
        self.worker = WorkerThread(
            op_code=op_code, tmtc_handler=self.tmtc_handler
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_worker)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.finished.connect(finish_callback)
        self.thread.start()

    def __add_vertical_separator(self, grid: QGridLayout, row: int):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        grid.addWidget(separator, row, 0, 1, 2)
        row += 1
        return row

    def __checkbox_log_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_TO_FILE, state)
        if self.debug_mode:
            LOGGER.info(["Enabled", "Disabled"][state == 0] + " print to log.")

    def __checkbox_console_update(self, state: bool):
        update_global(CoreGlobalIds.PRINT_TM, state)
        if self.debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " console print")

    def __checkbox_print_raw_data_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_RAW_TM, state)
        if self.debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " printing of raw data")

    def __service_index_changed(self, index: int):
        self.current_service = self.service_list[index]
        if self.debug_mode:
            LOGGER.info(f"Service index changed: {self.current_service[index]}")

    def __set_send_button(self, state: bool):
        self.__command_button.setEnabled(state)

    def __get_send_button(self):
        return self.__command_button.isEnabled()

    def __com_if_index_changed(self, index: int):
        self.current_com_if = self.com_if_list[index][0]
        if self.debug_mode:
            LOGGER.info(f"Communication IF updated: {self.com_if_list[index][1]}")


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
    # tmtcc_config.G_PRINT_HK_DATA = state == 0


def checkbox_short_display_mode(state: int):
    update_global(CoreGlobalIds.DISPLAY_MODE, state)
    LOGGER.info(["enabled", "disabled"][state == 0] + " short display mode")
    # tmtcc_config.G_DISPLAY_MODE = ["short", "long"][state == 0]


def number_timeout(value: float):
    update_global(CoreGlobalIds.TM_TIMEOUT, value)
    LOGGER.info("PUS TM timeout changed to: " + str(value))
    # tmtcc_config.G_TM_TIMEOUT = value


def number_timeout_factor(value: float):
    update_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR, value)
    LOGGER.info("PUS TM timeout factor changed to: " + str(value))
    # tmtcc_config.G_TC_SEND_TIMEOUT_FACTOR = value


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


# TODO: This should be a separate window where the user types in stuff and confirms it.
"""
grid.addWidget(QLabel("Client IP:"), row, 0, 1, 1)
grid.addWidget(QLabel("Board IP:"), row, 1, 1, 1)
row += 1

spin_client_ip = QLineEdit()
# TODO: set sensible min/max values
spin_client_ip.setInputMask("000.000.000.000;_")
spin_client_ip.textChanged.connect(ip_change_client)
grid.addWidget(spin_client_ip, row, 0, 1, 1)

spin_board_ip = QLineEdit()
# TODO: set sensible min/max values
spin_board_ip.setInputMask("000.000.000.000;_")
spin_board_ip.textChanged.connect(ip_change_board)
# spin_board_ip.setText(obsw_config.G_SEND_ADDRESS[0])
grid.addWidget(spin_board_ip, row, 1, 1, 1)

row += 1
"""

# This stuff will probably not used in this form.. the single command is specified in code and we only need
# a button to execute it.
"""

    def single_command_set_service(self, value):
        self.single_command_service = value

    def single_command_set_sub_service(self, value):
        self.single_command_sub_service = value

    def single_command_set_ssc(self, value):
        self.single_command_ssc = value
        
        single_command_grid = QGridLayout()
        single_command_grid.setSpacing(5)

        single_command_grid.addWidget(QLabel("Service: "), row, 0, 1, 1)
        single_command_grid.addWidget(QLabel("Subservice: "), row, 1, 1, 1)
        single_command_grid.addWidget(QLabel("SSC: "), row, 2, 1, 1)

        row += 1

        spin_service = QSpinBox()
        spin_service.setValue(self.single_command_service)
        # TODO: set sensible min/max values
        spin_service.setMinimum(0)
        spin_service.setMaximum(99999)
        spin_service.valueChanged.connect(self.single_command_set_service)
        single_command_grid.addWidget(spin_service, row, 0, 1, 1)

        spin_sub_service = QSpinBox()
        spin_sub_service.setValue(self.single_command_sub_service)
        # TODO: set sensible min/max values
        spin_sub_service.setMinimum(0)
        spin_sub_service.setMaximum(99999)
        spin_sub_service.valueChanged.connect(self.single_command_set_sub_service)
        single_command_grid.addWidget(spin_sub_service, row, 1, 1, 1)

        spin_ssc = QSpinBox()
        spin_ssc.setValue(self.single_command_ssc)
        # TODO: set sensible min/max values
        spin_ssc.setMinimum(0)
        spin_ssc.setMaximum(99999)
        spin_ssc.valueChanged.connect(self.single_command_set_ssc)
        single_command_grid.addWidget(spin_ssc, row, 2, 1, 1)

        # row += 1
        grid.addItem(single_command_grid, row, 0, 1, 2)
        # single_command_grid.addWidget(QLabel("Data: "), row, 0, 1, 3)

        row += 1

        # TODO: how should this be converted to the byte array?
        # single_command_data_box = QTextEdit()
        # single_command_grid.addWidget(single_command_data_box, row, 0, 1, 3)

        # row += 1

        self.commandTable = SingleCommandTable()
        # grid.addWidget(self.commandTable, row, 0, 1, 2)
        row += 1
                # resize table columns to fill the window width
        # for i in range(0, 5):
        #    self.commandTable.setColumnWidth(i, int(self.commandTable.width() / 5) - 3)

"""