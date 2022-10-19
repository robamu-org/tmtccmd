import time

from PyQt5.QtCore import QRunnable, pyqtSlot, QObject, pyqtSignal

from tmtccmd import get_console_logger
from tmtccmd.core import TmMode, TcMode, BackendRequest
from tmtccmd.gui.defs import LocalArgs, SharedArgs, WorkerOperationsCodes


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
                time.sleep(state.next_delay.seconds)
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
            get_console_logger().error(
                f"Unknown worker operation code {self._locals.op_code}"
            )
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
