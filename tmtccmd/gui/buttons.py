from typing import Callable, Optional

from PyQt5.QtCore import QThreadPool, QRunnable
from PyQt5.QtWidgets import QPushButton

from tmtccmd import HookBase, get_console_logger, DefaultProcedureInfo
from tmtccmd.gui.defs import (
    SharedArgs,
    LocalArgs,
    WorkerOperationsCodes,
    DISCONNECT_BTTN_STYLE,
    CONNECT_BTTN_STYLE,
    COMMAND_BUTTON_STYLE,
)
from tmtccmd.gui.defs import FrontendState
from tmtccmd.gui.worker import FrontendWorker

LOGGER = get_console_logger()


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
        hook_obj: HookBase,
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
        self._com_if_needs_switch = False
        self.button.clicked.connect(self._button_op)

    def _button_op(self):
        if not self._connected:
            self._connect_button_pressed()
        else:
            self._disconnect_button_pressed()

    def _connect_button_pressed(self):
        LOGGER.info("Opening COM Interface")
        self._com_if_needs_switch = False
        # Build and assign new communication interface
        if self._args.state.current_com_if != self._args.state.last_com_if:
            self._com_if_needs_switch = True
        self.button.setEnabled(False)
        worker = FrontendWorker(
            LocalArgs(
                WorkerOperationsCodes.OPEN_COM_IF,
                (
                    self._com_if_needs_switch,
                    self._args.state.current_com_if,
                    self._bttn_params.hook_obj,
                ),
            ),
            self._args.shared,
        )
        self._next_con_state = True
        worker.signals.finished.connect(self._button_op_done)
        # TODO: Connect failure signal as well
        self._args.pool.start(worker)

    def _button_op_done(self):
        if self._next_con_state:
            if self._com_if_needs_switch:
                self._args.state.last_com_if = self._args.state.current_com_if
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

    def is_listening(self):
        return self._listening

    def stop_thread(self):
        if self.worker:
            self.stop_listener()

    def abort_thread(self):
        if self.worker:
            self.worker.signals.abort.emit(None)

    def start_listener(self):
        LOGGER.info("Starting TM listener")
        self.worker = FrontendWorker(
            LocalArgs(WorkerOperationsCodes.LISTEN_FOR_TM, 0.4), self.args.shared
        )
        self._next_listener_state = True
        self._conn_button.setDisabled(True)
        self.args.pool.start(self.worker)
        self.button_op_done()

    def stop_listener(self):
        LOGGER.info("Stopping TM listener")
        self._next_listener_state = False
        self.worker.signals.finished.connect(self.button_op_done)
        self.worker.signals.stop.emit(None)
        self.button.setEnabled(False)

    def button_op(self):
        if not self._listening:
            self.start_listener()
        else:
            self.stop_listener()

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
        self._args.shared.backend.current_procedure = DefaultProcedureInfo(
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
