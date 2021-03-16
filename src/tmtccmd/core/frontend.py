#!/usr/bin/python3.7
"""
@file           tmtc_frontend.py
@date           01.11.2019
@brief          This is part of the TMTC client developed by the SOURCE project by KSat
@description    GUI is still work-in-progress
@manual
@author         R. Mueller, P. Scheurenbrand, D. Nguyen
"""
import threading
import os
from multiprocessing import Process

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QIcon

from tmtccmd.core.backend import TmTcHandler
from tmtccmd.core.definitions import CoreComInterfaces, CoreGlobalIds, CoreModeList
from tmtccmd.pus_tc.base import PusTelecommand
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.core.globals_manager import get_global, update_global
import tmtccmd.defaults as defaults_module

LOGGER = get_logger()


class TmTcFrontend(QMainWindow):

    # TODO: this list should probably be inside an enum in the tmtcc_config.py
    service_test_button: QPushButton
    single_command_button: QPushButton
    command_table: QTableWidget

    single_command_service: int = 17
    single_command_sub_service: int = 1
    single_command_ssc: int = 20
    single_command_data: bytearray = bytearray([])

    def __init__(self, init_com_if: CoreComInterfaces, init_mode: int, init_service: int):
        super(TmTcFrontend, self).__init__()
        self.tmtc_handler = TmTcHandler(init_com_if=init_com_if, init_mode=init_mode,
                                        init_service=init_service)
        # TODO: Perform initialization on button press with specified ComIF
        #       Also, when changing ComIF, ensure that old ComIF is closed (e.g. with printout)
        #       Lock all other elements while ComIF is invalid.
        self.tmtc_handler.initialize()
        self.service_list = []
        self.debug_mode = True
        self.is_busy = False
        module_path = os.path.abspath(defaults_module.__file__).replace("__init__.py", "")
        self.logo_path = f"{module_path}/logo.png"
        print(self.logo_path)
        self.tmtc_handler.start(False)

    def prepare_start(self, args: any) -> Process:
        return Process(target=self.start_ui)

    def set_gui_logo(self, logo_total_path: str):
        if os.path.isfile(logo_total_path):
            self.logo_path = logo_total_path
        else:
            LOGGER.warning("Could not set logo, path invalid!")

    def service_index_changed(self, index: int):
        self.tmtc_handler.service = self.service_list[index]
        if self.debug_mode:
            LOGGER.info("service_test_mode_selection updated: " + str(self.service_list[index]))

    def single_command_set_service(self, value):
        self.single_command_service = value

    def single_command_set_sub_service(self, value):
        self.single_command_sub_service = value

    def single_command_set_ssc(self, value):
        self.single_command_ssc = value

    def start_service_test_clicked(self):
        if self.debug_mode:
            LOGGER.info("Start Service Test Button pressed.")
        # LOGGER.info("start testing service: " + str(tmtcc_config.G_SERVICE))
        # self.tmtc_handler.mode = tmtcc_config.ModeList.ServiceTestMode
        # start the action in a new process
        p = threading.Thread(target=self.handle_tm_tc_action)
        p.start()

    def send_single_command_clicked(self, table):
        if self.debug_mode:
            LOGGER.info("Send Single Command Pressed.")

        # parse the values from the table
        # service = int(self.commandTable.item(0, 0).text())
        # subservice = int(self.commandTable.item(0, 1).text())
        # ssc = int(self.commandTable.item(0, 2).text())

        LOGGER.info("service: " + str(self.single_command_service) +
                    ", subservice: " + str(self.single_command_sub_service) +
                    ", ssc: " + str(self.single_command_ssc))

        # TODO: data needs to be parsed in a different way
        # data = int(self.commandTable.item(0, 3).text())
        # crc = int(self.commandTable.item(0, 4).text())

        # create a command out of the parsed table
        command = PusTelecommand(
            service=self.single_command_service, subservice=self.single_command_sub_service,
            ssc=self.single_command_ssc)
        self.tmtc_handler.single_command_package = command.pack_command_tuple()

        # self.tmtc_handler.mode = tmtcc_config.ModeList.SingleCommandMode
        # start the action in a new process
        p = threading.Thread(target=self.handle_tm_tc_action)
        p.start()

    def handle_tm_tc_action(self):
        if self.debug_mode:
            LOGGER.info("Starting TMTC action..")
        self.tmtc_handler.mode = CoreModeList.ServiceTestMode

        self.set_send_buttons(False)
        self.tmtc_handler.perform_operation()
        self.is_busy = False
        self.set_send_buttons(True)
        if self.debug_mode:
            LOGGER.info("Finished TMTC action..")

    def set_send_buttons(self, state: bool):
        self.service_test_button.setEnabled(state)
        self.single_command_button.setEnabled(state)

    def start_ui(self):

        win = QWidget(self)
        self.setCentralWidget(win)
        grid = QGridLayout()

        self.setWindowTitle("TMTC Commander")
        label = QLabel(self)
        pixmap = QPixmap(self.logo_path)  # QPixmap is the class, easy to put pic on screen
        label.setGeometry(720, 10, 100, 100)
        label.setPixmap(pixmap)
        self.setWindowIcon(QIcon(self.logo_path))
        label.setScaledContents(True)
        row = 0
        grid.addWidget(QLabel("Configuration:"), row, 0, 1, 2)
        row += 1

        checkbox_console = QCheckBox("Print output to console")
        checkbox_console.stateChanged.connect(self.checkbox_console_update)

        checkbox_log = QCheckBox("Print output to log file")
        checkbox_log.stateChanged.connect(self.checkbox_log_update)

        checkbox_raw_tm = QCheckBox("Print all raw TM data directly")
        checkbox_raw_tm.stateChanged.connect(self.checkbox_print_raw_data_update)

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
        # com if configuration
        grid.addWidget(QLabel("Communication Interface:"), row, 0, 1, 1)
        com_if_combo_box = QComboBox()
        # add all possible ComIFs to the comboBox
        for com_if in CoreComInterfaces:
            com_if_combo_box.addItem(str(com_if))
        com_if_combo_box.setCurrentIndex(self.tmtc_handler.com_if.value)
        com_if_combo_box.currentIndexChanged.connect(com_if_index_changed)
        grid.addWidget(com_if_combo_box, row, 1, 1, 1)
        row += 1

        # service test mode gui
        grid.addWidget(QLabel("Service Test Mode:"), row, 0, 1, 2)
        row += 1

        combo_box = QComboBox()

        service_dict = get_global(CoreGlobalIds.SERVICELIST)

        for service_key, service_value in service_dict.items():
            combo_box.addItem(service_dict[service_key][0])
            self.service_list.append(service_value)

        default_service = get_global(CoreGlobalIds.CURRENT_SERVICE)
        combo_box.setCurrentIndex(default_service.value)
        combo_box.currentIndexChanged.connect(self.service_index_changed)
        grid.addWidget(combo_box, row, 0, 1, 1)

        self.service_test_button = QPushButton()
        self.service_test_button.setText("Start Service Test")
        self.service_test_button.clicked.connect(self.start_service_test_clicked)
        grid.addWidget(self.service_test_button, row, 1, 1, 1)
        row += 1

        # single command operation
        grid.addWidget(QLabel("Single Command Operation:"), row, 0, 1, 1)
        row += 1

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

        row += 1

        single_command_grid.addWidget(QLabel("Data: "), row, 0, 1, 3)

        row += 1

        # TODO: how should this be converted to the byte array?
        single_command_data_box = QTextEdit()
        single_command_grid.addWidget(single_command_data_box, row, 0, 1, 3)

        grid.addItem(single_command_grid, row, 0, 1, 2)

        row += 1

        # self.commandTable = SingleCommandTable()
        # grid.addWidget(self.commandTable, row, 0, 1, 2)
        row += 1
        self.single_command_button = QPushButton()
        self.single_command_button.setText("Send single command: ")
        self.single_command_button.clicked.connect(self.send_single_command_clicked)
        grid.addWidget(self.single_command_button, row, 0, 1, 2)
        row += 1

        win.setLayout(grid)
        self.resize(900, 800)
        self.show()

        # resize table columns to fill the window width
        # for i in range(0, 5):
        #    self.commandTable.setColumnWidth(i, int(self.commandTable.width() / 5) - 3)

    def checkbox_log_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_TO_FILE, state)
        if self.debug_mode:
            LOGGER.info(["Enabled", "Disabled"][state == 0] + " print to log.")

    def checkbox_console_update(self, state: bool):
        update_global(CoreGlobalIds.PRINT_TM, state)
        if self.debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " console print")

    def checkbox_print_raw_data_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_RAW_TM, state)
        if self.debug_mode:
            LOGGER.info(["enabled", "disabled"][state == 0] + " printing of raw data")


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


def com_if_index_changed(index: int):
    update_global(CoreGlobalIds.COM_IF, CoreComInterfaces(index))
    LOGGER.info(f"Communication IF updated: {CoreComInterfaces(index)}")


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
    from config.custom_definitions import EthernetConfig
    ethernet_config = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_config[EthernetConfig.RECV_ADDRESS] = value
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_config)
    LOGGER.info("Client IP changed: " + value)


def ip_change_board(value):
    from config.custom_definitions import EthernetConfig
    ethernet_config = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_config[EthernetConfig.SEND_ADDRESS] = value
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_config)
    LOGGER.info("Board IP changed: " + value)
