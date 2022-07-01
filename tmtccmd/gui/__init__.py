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
from pathlib import Path
from typing import Union, Callable, Optional

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
    pyqtSignal,
    QObject,
    QRunnable,
    pyqtSlot,
    QThreadPool,
)

from tmtccmd.core.base import FrontendBase
from tmtccmd.config.globals import CoreGlobalIds
from tmtccmd.core import BackendController, TmMode, TcMode, BackendRequest
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.config import (
    TmTcCfgHookBase,
    CoreComInterfaces,
)
from tmtccmd.logging import get_console_logger
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.tcpip_utils import TcpIpConfigIds
import tmtccmd as mod_root
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
    finished = pyqtSignal(object)
    failure = pyqtSignal(object)
    stop = pyqtSignal(object)


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

    def __setup(self, op_code: WorkerOperationsCodes) -> bool:
        if op_code == WorkerOperationsCodes.OPEN_COM_IF:
            if self._shared.backend.com_if_active():
                self._finish_with_info("COM Interface is already active")
            else:
                self._shared.backend.open_com_if()
                self._finish_success()
            return False
        if op_code == WorkerOperationsCodes.CLOSE_COM_IF:
            if not self._shared.backend.com_if_active():
                self._finish_with_info("COM Interface is not active")
            elif self._shared.com_if_ref_tracker.is_used():
                self._failure_with_info("Can not close COM interface which is used")
            else:
                self._shared.backend.close_com_if()
                self._finish_success()
            return False
        if op_code == WorkerOperationsCodes.ONE_QUEUE_MODE:
            self._shared.com_if_ref_tracker.add_user()
            with self._shared.tc_lock:
                self._shared.backend.tc_mode = TcMode.ONE_QUEUE
        elif op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            self._shared.com_if_ref_tracker.add_user()
            self._shared.backend.tm_mode = TmMode.LISTENER
        return True

    def __loop(self, op_code: WorkerOperationsCodes) -> bool:
        if op_code == WorkerOperationsCodes.ONE_QUEUE_MODE:
            self._shared.tc_lock.acquire()
            self._shared.backend.tc_operation()
            self._update_backend_mode()
            state = self._shared.backend.state
            if state.request == BackendRequest.TERMINATION_NO_ERROR:
                self._shared.tc_lock.release()
                self._shared.com_if_ref_tracker.remove_user()
                with self._shared.state_lock:
                    if (
                        not self._shared.com_if_ref_tracker.is_used()
                        and self._locals.op_args is not None
                    ):
                        self._locals.op_args()
                self._finish_success()
                return False
            elif state.request == BackendRequest.DELAY_CUSTOM:
                self._shared.tc_lock.release()
                time.sleep(state.next_delay)
            elif state.request == BackendRequest.CALL_NEXT:
                self._shared.tc_lock.release()
        elif op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            if not self._stop_signal:
                # We only should run the TM operation here
                self._shared.backend.tm_operation()
                # Poll TM every 400 ms for now
                time.sleep(self._locals.op_args)
            else:
                self._shared.com_if_ref_tracker.remove_user()
                self._finish_success()
                return False
        elif op_code == WorkerOperationsCodes.IDLE:
            return False
        else:
            # This must be a programming error
            LOGGER.error(f"Unknown worker operation code {self._locals.op_code}")
        return True

    @pyqtSlot()
    def run(self):
        op_code = self._locals.op_code
        loop_required = self.__setup(op_code)
        if loop_required:
            while True:
                if not self.__loop(op_code):
                    break

    def _finish_success(self):
        self.signals.finished.emit(None)

    def _finish_with_info(self, info: str):
        self.signals.finished.emit(info)

    def _failure_with_info(self, info: str):
        self.signals.failure.emit(info)

    def _update_backend_mode(self):
        with self._shared.state_lock:
            self._shared.backend.mode_to_req()

    def _stop_com_if(self, _args: any):
        self._stop_signal = True


class FrontendState:
    def __init__(self):
        self.current_com_if = CoreComInterfaces.UNSPECIFIED.value
        self.current_service = ""
        self.current_op_code = ""
        self.auto_connect_tm_listener = True
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


class ConnectButtonParams:
    def __init__(
        self,
        hook_obj: TmTcCfgHookBase,
        connect_cb: Callable[[], None],
        disconnect_cb: Callable[[], None],
        tm_listener_bttn: Optional[QPushButton],
    ):
        self.hook_obj = hook_obj
        self.connect_cb = connect_cb
        self.disconnect_cb = disconnect_cb
        self.tm_listener_bttn = tm_listener_bttn


class ConnectButtonWrapper:
    def __init__(
        self, button: QPushButton, args: ButtonArgs, bttn_params: ConnectButtonParams
    ):
        self.button = button
        self._args = args
        self._bttn_params = bttn_params
        self._connected = False
        self._next_con_state = False
        self.button.clicked.connect(self._button_op)

    def _button_op(self):
        if not self._connected:
            self._connect_button_pressed()
        else:
            self._disconnect_button_pressed()

    def _connect_button_pressed(self):
        LOGGER.info("Opening COM Interface")
        # Build and assign new communication interface
        if self._args.state.current_com_if != self._args.state.last_com_if:
            LOGGER.info("Switching COM Interface")
            new_com_if = self._bttn_params.hook_obj.assign_communication_interface(
                com_if_key=self._args.state.current_com_if
            )
            self._args.state.last_com_if = self._args.state.current_com_if
            self._args.shared.backend.try_set_com_if(new_com_if)
        self.button.setEnabled(False)
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.OPEN_COM_IF, None), self._args.shared
        )
        self._next_con_state = True
        worker.signals.finished.connect(self._button_op_done)
        # TODO: Connect failure signal as well
        self._args.pool.start(worker)

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
        self._bttn_params.connect_cb()
        if (
            self._args.state.auto_connect_tm_listener
            and self._bttn_params.tm_listener_bttn is not None
        ):
            self._bttn_params.tm_listener_bttn.click()
        LOGGER.info("Connected")

    def _disconnect_button_pressed(self):
        self.button.setEnabled(False)
        self._next_con_state = False
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.CLOSE_COM_IF, None), self._args.shared
        )
        worker.signals.finished.connect(self._button_op_done)
        self._args.pool.start(worker)

    def _disconnect_button_finished(self):
        self.button.setEnabled(True)
        self.button.setStyleSheet(CONNECT_BTTN_STYLE)
        self.button.setText("Connect")
        self._bttn_params.disconnect_cb()
        LOGGER.info("Disconnected")


class TmButtonWrapper:
    def __init__(self, button: QPushButton, args: ButtonArgs, conn_button: QPushButton):
        self.button = button
        self.args = args
        self.worker: Optional[QRunnable] = None
        self._listening = False
        self._next_listener_state = False
        self.button.setStyleSheet(CONNECT_BTTN_STYLE)
        self.button.setText("Start TM listener")
        self.button.setEnabled(False)
        self.button.clicked.connect(self.button_op)
        self._conn_button = conn_button

    def button_op(self):
        if not self._listening:
            LOGGER.info("Starting TM listener")
            self.worker = FrontendWorker(
                LocalArgs(WorkerOperationsCodes.LISTEN_FOR_TM, 0.4), self.args.shared
            )
            self._next_listener_state = True
            self._conn_button.setDisabled(True)
            self.args.pool.start(self.worker)
            self.button_op_done()
        else:
            LOGGER.info("Stopping TM listener")
            self._next_listener_state = False
            self.worker.signals.finished.connect(self.button_op_done)
            self.worker.signals.stop.emit(None)
            self.button.setEnabled(False)

    def button_op_done(self):
        if self._next_listener_state:
            self.button.setStyleSheet(DISCONNECT_BTTN_STYLE)
            self.button.setText("Stop TM listener")
            self._listening = True
            self.button.setEnabled(True)
        else:
            self.button.setStyleSheet(CONNECT_BTTN_STYLE)
            if not self.args.shared.com_if_ref_tracker.is_used():
                self._conn_button.setEnabled(True)
            self.button.setText("Start TM listener")
            self._listening = False
        self.button.setEnabled(True)


class SendButtonWrapper:
    def __init__(self, button: QPushButton, args: ButtonArgs, conn_button: QPushButton):
        self.button = button
        self._args = args
        self._conn_button = conn_button
        self.debug_mode = False
        self.button.setText("Send Command")
        self.button.setStyleSheet(COMMAND_BUTTON_STYLE)
        self.button.setEnabled(False)
        self.button.clicked.connect(self._button_op)

    def _button_op(self):
        if self.debug_mode:
            LOGGER.info("Send command button pressed.")
        self.button.setDisabled(True)
        self._args.shared.backend.current_proc_info = DefaultProcedureInfo(
            self._args.state.current_service, self._args.state.current_op_code
        )
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.ONE_QUEUE_MODE, None), self._args.shared
        )
        worker.signals.finished.connect(self._finish_op)
        self._args.pool.start(worker)

    def _finish_op(self):
        self.button.setEnabled(True)
        if not self._args.shared.com_if_ref_tracker.is_used():
            self._conn_button.setEnabled(True)


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
        self.logo_path = Path(f"{Path(mod_root.__file__).parent.parent}/misc/logo.png")

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
        print(self.logo_path)
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
        self._current_service = self._service_list[index]
        self.__update_op_code_combo_box()
        if self.__debug_mode:
            LOGGER.info("Service changed")

    def __op_code_index_changed(self, index: int):
        self._state.current_op_code = self._op_code_list[index]
        if self.__debug_mode:
            LOGGER.info("Op Code changed")

    def __update_op_code_combo_box(self):
        self.__combo_box_op_codes.clear()
        self._op_code_list = []
        op_code_entry = self._service_op_code_dict.op_code_entry(
            self._state.current_service
        )
        if op_code_entry is not None:
            for op_code_key, op_code_value in op_code_entry.op_code_dict.items():
                try:
                    self._op_code_list.append(op_code_key)
                    self.__combo_box_op_codes.addItem(op_code_value[0])
                except TypeError:
                    LOGGER.warning(f"Invalid op code entry {op_code_value}, skipping..")
            self._state.current_op_code = self._op_code_list[0]

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
