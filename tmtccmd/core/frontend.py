"""PyQt front end components for the tmtccmd framework.
@author         R. Mueller, P. Scheurenbrand, D. Nguyen
"""
import enum
import os
import sys
import threading
import time
import webbrowser
from multiprocessing import Process
from typing import Union, Callable

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
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
    QObject,
    QRunnable,
    pyqtSlot,
    QThreadPool,
)

from tmtccmd.config.globals import CoreGlobalIds
from tmtccmd.core import BackendController, TmMode, TcMode, Request
from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.config import (
    TmTcCfgHookBase,
    CoreComInterfaces,
)
from tmtccmd.logging import get_console_logger
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.tcpip_utils import TcpIpConfigIds
import tmtccmd.config as config_module
from tmtccmd.tc import DefaultProcedureInfo

LOGGER = get_console_logger()


CONNECT_BTTN_STYLE = (
    "background-color: #1fc600;"
    "border-style: inset;"
    "font: bold;"
    "padding: 6px;"
    "border-width: 2px;"
    "border-radius: 6px;"
)


DISCONNECT_BTTN_STYLE = (
    "background-color: orange;"
    "border-style: inset;"
    "font: bold;"
    "padding: 6px;"
    "border-width: 2px;"
    "border-radius: 6px;"
)


COMMAND_BUTTON_STYLE = (
    "background-color: #cdeefd;"
    "border-style: inset;"
    "font: bold;"
    "padding: 6px;"
    "border-width: 2px;"
    "border-radius: 6px;"
)


class WorkerOperationsCodes(enum.IntEnum):
    OPEN_COM_IF = 0
    CLOSE_COM_IF = 1
    ONE_QUEUE_MODE = 2
    LISTEN_FOR_TM = 3
    UPDATE_BACKEND_MODE = 4
    IDLE = 5


class ComIfRefCount:
    def __init__(self):
        self.lock = threading.Lock()
        self.com_if_used = False
        self.user_cnt = 0

    def add_user(self):
        with self.lock:
            self.user_cnt += 1

    def remove_user(self):
        with self.lock:
            if self.user_cnt > 0:
                self.user_cnt -= 1

    def is_used(self):
        with self.lock:
            if self.user_cnt > 0:
                return True
            return False


class LocalArgs:
    def __init__(self, op_code: WorkerOperationsCodes, op_code_args: any = None):
        self.op_code = op_code
        self.op_args = op_code_args


class SharedArgs:
    def __init__(self, backend: CcsdsTmtcBackend):
        self.ctrl = BackendController()
        self.state_lock = threading.Lock()
        self.com_if_ref_tracker = ComIfRefCount()
        self.tc_lock = threading.Lock()
        self.backend = backend


class WorkerSignalWrapper(QObject):
    finished = pyqtSignal()
    failure = pyqtSignal(str)
    stop = pyqtSignal()


class FrontendWorker(QRunnable):
    """Runnable thread which can be used with QThreadPool. Not used for now, might be needed
    in the future.
    """

    def __init__(self, local_args: LocalArgs, shared_args: SharedArgs):
        super(QRunnable, self).__init__()
        self._locals = local_args
        self._shared = shared_args
        self.signals = WorkerSignalWrapper()
        self._stop_signal = False
        self.signals.stop.connect(self._stop_com_if)

    def __sanitize_locals(self):
        if self._locals.op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            if self._locals.op_args is None or not isinstance(
                float, self._locals.op_args
            ):
                self._locals.op_args = 0.2

    def __setup_worker(self) -> bool:
        self._stop_signal = True
        if self._locals.op_code == WorkerOperationsCodes.CLOSE_COM_IF:
            if self._shared.com_if_ref_tracker.is_used():
                self.signals.failure.emit("Can not close COM interface which is used")
                return False
        if self._locals.op_code == WorkerOperationsCodes.ONE_QUEUE_MODE:
            self._shared.com_if_ref_tracker.add_user()
            with self._shared.tc_lock:
                self._shared.backend.tc_mode = TcMode.ONE_QUEUE
        elif self._locals.op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            self._shared.com_if_ref_tracker.add_user()
            with self._shared.state_lock:
                if not self._shared.com_if_used:
                    self._shared.com_if_used = True
            self._shared.backend.tm_mode = TmMode.LISTENER
        return True

    @pyqtSlot()
    def run(self):
        if not self.__setup_worker():
            return
        while True:
            op_code = self._locals.op_code
            if op_code == WorkerOperationsCodes.OPEN_COM_IF:
                if self._shared.backend.com_if_active():
                    break
                else:
                    self._shared.backend.open_com_if()
                self.signals.finished.emit()
            elif op_code == WorkerOperationsCodes.CLOSE_COM_IF:
                self._shared.backend.close_com_if()
                # TODO: Maybe there will be cases where closing a COM IF takes time and success
                #       must be tracked by polling the COM IF / Backend
                while True:
                    if not self._shared.backend.com_if_active():
                        break
                    else:
                        # The sleep duration was sanitized before and should be a valid float now
                        time.sleep(0.2)
                self.signals.finished.emit()
                break
            elif op_code == WorkerOperationsCodes.ONE_QUEUE_MODE:
                self._shared.tc_lock.acquire()
                self._shared.backend.tc_mode = TcMode.ONE_QUEUE
                self._shared.backend.tc_operation()
                state = self._shared.backend.state
                if state.request == Request.TERMINATION_NO_ERROR:
                    self._shared.tc_lock.release()
                    self._shared.com_if_ref_tracker.remove_user()
                    self.signals.finished.emit()
                    break
                elif state.request == Request.DELAY_CUSTOM:
                    self._shared.tc_lock.release()
                    self._update_backend_mode()
                    time.sleep(state.next_delay)
                elif state.request == Request.CALL_NEXT:
                    self._shared.tc_lock.release()
            elif op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
                if not self._stop_signal:
                    # We only should run the TM operation here
                    self._shared.backend.tm_operation()
                    # Poll TM every 400 ms for now
                    time.sleep(self._locals.op_args)
                else:
                    self._shared.com_if_ref_tracker.remove_user()
            elif op_code == WorkerOperationsCodes.IDLE:
                break
            else:
                # This must be a programming error
                LOGGER.error(f"Unknown worker operation code {self._locals.op_code}")

    def _update_backend_mode(self):
        with self._shared.state_lock:
            self._shared.backend.mode_to_req()

    def _stop_com_if(self):
        self._stop_signal = True


class FrontendState:
    def __init__(self):
        self.current_com_if = CoreComInterfaces.UNSPECIFIED.value
        self.current_service = ""
        self.current_op_code = ""
        self.last_com_if = CoreComInterfaces.UNSPECIFIED.value
        self.current_com_if_key = CoreComInterfaces.UNSPECIFIED.value


class ButtonArgs:
    def __init__(
        self,
        state: FrontendState,
        pool: QThreadPool,
        shared: SharedArgs,
    ):
        self.state = state
        self.pool = pool
        self.shared = shared


class ConnectButtonWrapper:
    def __init__(
        self,
        button: QPushButton,
        args: ButtonArgs,
        hook_obj: TmTcCfgHookBase,
        connect_cb: Callable[[], None],
        disconnect_cb: Callable[[], None],
    ):
        self.button = button
        self.args = args
        self.hook_obj = hook_obj
        self._connected = False
        self._next_con_state = False
        self.button.clicked.connect(self._button_op)
        self._connect_cb = connect_cb
        self._disconnect_cb = disconnect_cb

    def _button_op(self):
        if not self._connected:
            self._connect_button_pressed()
        else:
            self._disconnect_button_pressed()

    def _connect_button_pressed(self):
        LOGGER.info("Opening COM Interface")
        # Build and assign new communication interface
        if self.args.state.current_com_if != self.args.state.last_com_if:
            LOGGER.info("Switching COM Interface")
            new_com_if = self.hook_obj.assign_communication_interface(
                com_if_key=self.args.state.current_com_if
            )
            self.args.state.last_com_if = self.args.state.current_com_if
            self.args.shared.backend.try_set_com_if(new_com_if)
        self.button.setEnabled(False)
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.OPEN_COM_IF, None), self.args.shared
        )
        self._next_con_state = True
        worker.signals.finished.connect(self._button_op_done)
        # TODO: Connect failure signal as well
        self.args.pool.start(worker)

    def _button_op_done(self):
        if self._next_con_state:
            self._connect_button_finished()
        else:
            self._disconnect_button_finished()
        self._connected = self._next_con_state

    def _connect_button_finished(self):
        self.button.setStyleSheet(DISCONNECT_BTTN_STYLE)
        self.button.setText("Disconnect")
        self.button.setEnabled(True)
        self._connect_cb()
        LOGGER.info("Connected")

    def _disconnect_button_pressed(self):
        self.button.setEnabled(False)
        self._next_con_state = False
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.CLOSE_COM_IF, None), self.args.shared
        )
        worker.signals.finished.connect(self._button_op_done)
        self.args.pool.start(worker)

    def _disconnect_button_finished(self):
        self.button.setEnabled(True)
        self.button.setStyleSheet(CONNECT_BTTN_STYLE)
        self.button.setText("Connect")
        self._disconnect_cb()
        LOGGER.info("Disconnected")


class TmTcFrontend(QMainWindow, FrontendBase):
    def __init__(
        self, hook_obj: TmTcCfgHookBase, tmtc_backend: CcsdsTmtcBackend, app_name: str
    ):
        super(TmTcFrontend, self).__init__()
        super(QMainWindow, self).__init__()
        self._app_name = app_name
        self._shared_args = SharedArgs(tmtc_backend)
        self._hook_obj = hook_obj
        self._service_list = []
        self._op_code_list = []
        self._com_if_list = []
        self._service_op_code_dict = hook_obj.get_tmtc_definitions()
        self._state = FrontendState()
        self._thread_pool = QThreadPool()
        self.__connected = False
        self.__debug_mode = True

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
        row, self.__connect_button_wrapper = self.__set_up_com_if_section(
            grid=grid, row=row
        )
        row = self.__add_vertical_separator(grid=grid, row=row)

        row = self.__set_up_service_op_code_section(grid=grid, row=row)

        self.__command_button = QPushButton()
        self.__command_button.setText("Send Command")
        self.__command_button.setStyleSheet(COMMAND_BUTTON_STYLE)
        self.__command_button.clicked.connect(self.__start_seq_cmd_op)
        self.__command_button.setEnabled(False)
        grid.addWidget(self.__command_button, row, 0, 1, 2)
        row += 1

        self.__listener_button = QPushButton()
        self.__listener_button.setText("Activate TM listener")
        self.__listener_button.setStyleSheet(COMMAND_BUTTON_STYLE)
        self.__listener_button.clicked.connect(self.__start_listener)
        self.__listener_button.setEnabled(False)
        grid.addWidget(self.__listener_button, row, 0, 1, 2)
        row += 1
        self.show()

    def __start_seq_cmd_op(self):
        if self.__debug_mode:
            LOGGER.info("Send command button pressed.")
        if not self.__get_send_button():
            return
        self.__disable_send_button()
        self._shared_args.backend.current_proc_info = DefaultProcedureInfo(
            self._current_service, self._current_op_code
        )
        self._shared_args.backend.tc_mode = TcMode.ONE_QUEUE
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.ONE_QUEUE_MODE, None), self._shared_args
        )
        # We need to call this stop signal on a button press..
        # worker.signals.stop.emit()
        worker.signals.finished.connect(self.__finish_seq_cmd_op)
        self._thread_pool.start(worker)

    def __start_listener(self):
        pass

    def __finish_seq_cmd_op(self):
        self.__enable_send_button()

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

    def __set_up_com_if_section(
        self, grid: QGridLayout, row: int
    ) -> (int, ConnectButtonWrapper):
        grid.addWidget(QLabel("Communication Interface:"), row, 0, 1, 1)
        com_if_combo_box = QComboBox()
        all_com_ifs = self._hook_obj.get_com_if_dict()
        index = 0
        # add all possible ComIFs to the comboBox
        for id, com_if_value in all_com_ifs.items():
            com_if_combo_box.addItem(com_if_value[0])
            self._com_if_list.append((id, com_if_value[0]))
            if self._shared_args.backend.com_if_id == id:
                com_if_combo_box.setCurrentIndex(index)
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
            hook_obj=self._hook_obj,
            button=connect_button,
            args=ButtonArgs(self._state, self._thread_pool, self._shared_args),
            connect_cb=self.__connected_com_if_cb,
            disconnect_cb=self.__disconnect_com_if_cb,
        )
        grid.addWidget(connect_button, row, 0, 1, 2)
        row += 1
        return row, conn_bttn_wrapper

    def __connected_com_if_cb(self):
        self.__enable_send_button()
        self.__enable_listener_button()

    def __disconnect_com_if_cb(self):
        self.__disable_send_button()
        self.__disable_listener_button()

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
        self._current_service = self._service_list[default_index]

        combo_box_services.currentIndexChanged.connect(self.__service_index_changed)
        grid.addWidget(combo_box_services, row, 0, 1, 1)

        self.__combo_box_op_codes = QComboBox()
        self._current_service = self._service_list[default_index]
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
        op_code_entry = self._service_op_code_dict.op_code_entry(self._current_service)
        if op_code_entry is not None:
            for op_code_key, op_code_value in op_code_entry.op_code_dict.items():
                try:
                    self._op_code_list.append(op_code_key)
                    self.__combo_box_op_codes.addItem(op_code_value[0])
                except TypeError:
                    LOGGER.warning(f"Invalid op code entry {op_code_value}, skipping..")
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

    def __enable_send_button(self):
        self.__command_button.setEnabled(True)

    def __disable_send_button(self):
        self.__command_button.setDisabled(True)

    def __enable_listener_button(self):
        self.__listener_button.setEnabled(True)

    def __disable_listener_button(self):
        self.__listener_button.setDisabled(True)

    def __get_send_button(self):
        return self.__command_button.isEnabled()

    def __com_if_sel_index_changed(self, index: int):
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
