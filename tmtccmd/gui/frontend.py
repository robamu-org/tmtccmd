"""PyQt front end components for the tmtccmd framework.
@author         R. Mueller, P. Scheurenbrand, D. Nguyen
"""
import os
import sys
import webbrowser
from multiprocessing import Process
from pathlib import Path
from typing import Union

from PyQt5.QtWidgets import (
    QMainWindow,
    QGridLayout,
    QTableWidget,
    QWidget,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QMenu,
    QAction,
)
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtCore import (
    Qt,
    QThreadPool,
)

from tmtccmd.core.base import FrontendBase
from tmtccmd.config.globals import CoreGlobalIds
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.config import HookBase
from tmtccmd.gui.buttons import (
    ConnectButtonParams,
    ButtonArgs,
    SendButtonWrapper,
    TmButtonWrapper,
    ConnectButtonWrapper,
)
from tmtccmd.gui.defs import SharedArgs, CONNECT_BTTN_STYLE, FrontendState
from tmtccmd.logging import get_console_logger
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com.tcpip_utils import TcpIpConfigIds
import tmtccmd as mod_root

LOGGER = get_console_logger()


class TmTcFrontend(QMainWindow, FrontendBase):
    def __init__(
        self, hook_obj: HookBase, tmtc_backend: CcsdsTmtcBackend, app_name: str
    ):
        super(TmTcFrontend, self).__init__()
        super(QMainWindow, self).__init__()
        self._app_name = app_name
        self._shared_args = SharedArgs(tmtc_backend)
        tmtc_backend.exit_on_com_if_init_failure = False
        self._hook_obj = hook_obj
        self._service_list = []
        self._op_code_list = []
        self._com_if_list = []
        self._service_op_code_dict = hook_obj.get_tmtc_definitions()
        self._state = FrontendState()
        self._thread_pool = QThreadPool()
        self.__connected = False

        self.__combo_box_op_codes: Union[None, QComboBox] = None
        self.logo_path = Path(
            f"{Path(mod_root.__file__).parent.parent}/misc/logo-tiny.png"
        )

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
        self.setWindowIcon(QIcon(self.logo_path.as_posix()))

        add_pixmap = False

        if add_pixmap:
            row = self.__set_up_pixmap(grid=grid, row=row)

        row = self.__set_up_config_section(grid=grid, row=row)
        row = self.__add_vertical_separator(grid=grid, row=row)

        tm_listener_button = QPushButton()
        conn_bttn_params = ConnectButtonParams(
            hook_obj=self._hook_obj,
            connect_cb=self.__connected_com_if_cb,
            disconnect_cb=self.__disconnect_com_if_cb,
            tm_listener_bttn=tm_listener_button,
        )
        # com if configuration
        row, self.__connect_button_wrapper = self.__set_up_com_if_section(
            conn_bttn_params=conn_bttn_params, grid=grid, row=row
        )
        row = self.__add_vertical_separator(grid=grid, row=row)

        tmtc_ctrl_label = QLabel("TMTC Control")
        font = QFont()
        font.setBold(True)
        tmtc_ctrl_label.setFont(font)
        grid.addWidget(tmtc_ctrl_label, row, 0, 1, 2)
        row += 1
        row = self.__set_up_service_op_code_section(grid=grid, row=row)

        button_args = ButtonArgs(
            state=self._state, pool=self._thread_pool, shared=self._shared_args
        )
        self.__send_bttn_wrapper = SendButtonWrapper(
            button=QPushButton(),
            args=button_args,
            conn_button=self.__connect_button_wrapper.button,
        )
        grid.addWidget(self.__send_bttn_wrapper.button, row, 0, 1, 2)
        row += 1

        self.__tm_button_wrapper = TmButtonWrapper(
            button=tm_listener_button,
            args=button_args,
            conn_button=self.__connect_button_wrapper.button,
        )
        grid.addWidget(self.__tm_button_wrapper.button, row, 0, 1, 2)
        row += 1
        self.show()
        # self.destroyed.connect(self.__tm_button_wrapper.stop_thread)

    def closeEvent(self, event):
        try:
            pass
            if self.__tm_button_wrapper.is_listening():
                LOGGER.warning("TM listener still active. Stopping it first..")
                self.__tm_button_wrapper.stop_thread()
                event.ignore()
            else:
                pass
        except KeyboardInterrupt:
            self.__tm_button_wrapper.abort_thread()

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
        webbrowser.open("https://tmtccmd.readthedocs.io/en/latest/")

    def __set_up_config_section(self, grid: QGridLayout, row: int) -> int:
        label = QLabel("Configuration")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        grid.addWidget(label, row, 0, 1, 2)
        row += 1

        start_listener_on_connect = QCheckBox("Auto-Connect TM listener")
        start_listener_on_connect.setChecked(True)
        start_listener_on_connect.stateChanged.connect(
            lambda: self._tm_auto_connect_changed(start_listener_on_connect)
        )
        grid.addWidget(start_listener_on_connect, row, 0, 1, 1)
        row += 1

        grid.addWidget(QLabel("Inter-Packet Delay Seconds [0 - 500]"), row, 0, 1, 2)
        row += 1

        spin_timeout = QDoubleSpinBox()
        spin_timeout.setValue(0.1)
        # TODO: set sensible min/max values
        spin_timeout.setSingleStep(0.1)
        spin_timeout.setMinimum(0.0)
        spin_timeout.setMaximum(500.0)
        # https://youtrack.jetbrains.com/issue/PY-22908
        # Ignore those warnings for now.
        spin_timeout.valueChanged.connect(number_timeout)
        grid.addWidget(spin_timeout, row, 0, 1, 1)
        row += 1
        return row

    def _tm_auto_connect_changed(self, box: QCheckBox):
        if box.isChecked():
            self._state.auto_connect_tm_listener = True
        else:
            self._state.auto_connect_tm_listener = False

    def __set_up_com_if_section(
        self, conn_bttn_params: ConnectButtonParams, grid: QGridLayout, row: int
    ) -> (int, ConnectButtonWrapper):
        font = QFont()
        font.setBold(True)
        label = QLabel("Communication Interface")
        label.setFont(font)
        grid.addWidget(label, row, 0, 1, 1)
        com_if_combo_box = QComboBox()
        all_com_ifs = self._hook_obj.get_com_if_dict()
        index = 0
        # add all possible ComIFs to the comboBox
        for id, com_if_value in all_com_ifs.items():
            com_if_combo_box.addItem(com_if_value[0])
            self._com_if_list.append((id, com_if_value[0]))
            if self._shared_args.backend.com_if_id == id:
                com_if_combo_box.setCurrentIndex(index)
                self._state.current_com_if = id
            index += 1
        com_if_combo_box.currentIndexChanged.connect(self.__com_if_sel_index_changed)
        grid.addWidget(com_if_combo_box, row, 1, 1, 1)
        row += 1

        self.com_if_cfg_button = QPushButton()
        self.com_if_cfg_button.setText("Configure")
        grid.addWidget(self.com_if_cfg_button, row, 0, 1, 2)
        row += 1

        connect_button = QPushButton()
        connect_button.setText("Connect")
        connect_button.setStyleSheet(CONNECT_BTTN_STYLE)
        conn_bttn_wrapper = ConnectButtonWrapper(
            button=connect_button,
            args=ButtonArgs(self._state, self._thread_pool, self._shared_args),
            bttn_params=conn_bttn_params,
        )
        grid.addWidget(connect_button, row, 0, 1, 2)
        row += 1
        return row, conn_bttn_wrapper

    def __disable_conn_bttn(self):
        self.__connect_button_wrapper.button.setDisabled(True)

    def __enable_conn_bttn(self):
        self.__connect_button_wrapper.button.setEnabled(True)

    def __connected_com_if_cb(self):
        self.__send_bttn_wrapper.button.setEnabled(True)
        self.__tm_button_wrapper.button.setEnabled(True)

    def __disconnect_com_if_cb(self):
        self.__send_bttn_wrapper.button.setDisabled(True)
        self.__tm_button_wrapper.button.setDisabled(True)

    def __set_up_service_op_code_section(self, grid: QGridLayout, row: int):
        grid.addWidget(QLabel("Service: "), row, 0, 1, 2)
        grid.addWidget(QLabel("Operation Code: "), row, 1, 1, 2)
        row += 1

        combo_box_services = QComboBox()
        default_service = get_global(CoreGlobalIds.CURRENT_SERVICE)
        self._service_op_code_dict = self._hook_obj.get_tmtc_definitions()
        if self._service_op_code_dict is None:
            LOGGER.warning("Invalid service to operation code dictionary")
            LOGGER.warning("Setting default dictionary")
            from tmtccmd.config.globals import get_default_tmtc_defs

            self._service_op_code_dict = get_default_tmtc_defs()
        index = 0
        default_index = 0
        for service_key, service_value in self._service_op_code_dict.defs.items():
            combo_box_services.addItem(service_value[0])
            if service_key == default_service:
                default_index = index
            self._service_list.append(service_key)
            index += 1
        combo_box_services.setCurrentIndex(default_index)
        self._state.current_service = self._service_list[default_index]

        combo_box_services.currentIndexChanged.connect(self.__service_index_changed)
        grid.addWidget(combo_box_services, row, 0, 1, 1)

        self.__combo_box_op_codes = QComboBox()
        self._state.current_service = self._service_list[default_index]
        self.__update_op_code_combo_box()
        self.__combo_box_op_codes.currentIndexChanged.connect(
            self.__op_code_index_changed
        )
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

        pixmap_scaled = pixmap.scaled(
            pixmap_width * 0.3, pixmap_height * 0.3, Qt.KeepAspectRatio
        )
        label.setPixmap(pixmap_scaled)
        label.setScaledContents(True)

        grid.addWidget(label, row, 0, 1, 2)
        row += 1
        return row

    @staticmethod
    def __add_vertical_separator(grid: QGridLayout, row: int):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        grid.addWidget(separator, row, 0, 1, 2)
        row += 1
        return row

    def __service_index_changed(self, index: int):
        self._state.current_service = self._service_list[index]
        self.__update_op_code_combo_box()
        LOGGER.debug("Service changed")

    def __op_code_index_changed(self, index: int):
        self._state.current_op_code = self._op_code_list[index]
        LOGGER.debug("Op Code changed")

    def __update_op_code_combo_box(self):
        self.__combo_box_op_codes.clear()
        self._op_code_list = []
        op_code_entry = self._service_op_code_dict.op_code_entry(
            self._state.current_service
        )
        if op_code_entry is not None:
            for (
                op_code_key,
                op_code_value,
            ) in op_code_entry.op_code_dict_num_keys.items():
                try:
                    self._op_code_list.append(op_code_key)
                    self.__combo_box_op_codes.addItem(op_code_value[0])
                except TypeError:
                    LOGGER.warning(f"Invalid op code entry {op_code_value}, skipping..")
            for (
                op_code_key,
                op_code_value,
            ) in op_code_entry.op_code_dict_str_keys.items():
                try:
                    self._op_code_list.append(op_code_key)
                    self.__combo_box_op_codes.addItem(op_code_value[0])
                except TypeError:
                    LOGGER.warning(f"Invalid op code entry {op_code_value}, skipping..")
            self._state.current_op_code = self._op_code_list[0]

    def __checkbox_log_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_TO_FILE, state)
        LOGGER.debug(["Enabled", "Disabled"][state == 0] + " print to log.")

    def __checkbox_console_update(self, state: bool):
        update_global(CoreGlobalIds.PRINT_TM, state)
        LOGGER.debug(["enabled", "disabled"][state == 0] + " console print")

    def __checkbox_print_raw_data_update(self, state: int):
        update_global(CoreGlobalIds.PRINT_RAW_TM, state)
        LOGGER.debug(["enabled", "disabled"][state == 0] + " printing of raw data")

    def __com_if_sel_index_changed(self, index: int):
        self._state.current_com_if = self._com_if_list[index][0]
        LOGGER.debug(f"Communication IF updated: {self._com_if_list[index][1]}")


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
