import logging
import time
from typing import Optional

from PyQt5.QtCore import QRunnable, pyqtSlot, QObject, pyqtSignal

from tmtccmd.core import TmMode, TcMode, BackendRequest
from tmtccmd.gui.defs import LocalArgs, SharedArgs, WorkerOperationsCodes


LOGGER = logging.getLogger(__name__)


class WorkerSignalWrapper(QObject):
    finished = pyqtSignal(object)
    failure = pyqtSignal(object)
    stop = pyqtSignal(object)
    abort = pyqtSignal(object)


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
        self._abort_signal = False
        self.signals.stop.connect(self._stop_com_if)
        self.signals.abort.connect(self._abort)

    def __sanitize_locals(self):
        if self._locals.op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            if self._locals.op_args is None or not isinstance(
                float, self._locals.op_args
            ):
                self._locals.op_args = 0.2

    def __setup(self, op_code: WorkerOperationsCodes) -> bool:
        if op_code == WorkerOperationsCodes.OPEN_COM_IF:
            LOGGER.info("Switching COM Interface")
            # TODO: We should really pass a proper object here instead of using magic tuples..
            new_com_if = self._locals.op_args[2].assign_communication_interface(
                com_if_key=self._locals.op_args[1]
            )
            # self._args.state.last_com_if = self._args.state.current_com_if
            set_success = self._shared.backend.try_set_com_if(new_com_if)
            if not set_success:
                LOGGER.warning(
                    f"Could not set new communication interface {new_com_if}"
                )
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

    def __one_queue_mode_cycle(self) -> Optional[bool]:
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
        elif state.request == BackendRequest.DELAY_IDLE:
            time.sleep(1.0)
        elif state.request == BackendRequest.DELAY_CUSTOM:
            self._shared.tc_lock.release()
            if state.next_delay.total_seconds() < 0.5:
                time.sleep(state.next_delay.total_seconds())
            else:
                time.sleep(0.5)
        elif state.request == BackendRequest.CALL_NEXT:
            self._shared.tc_lock.release()

    def __listener_cycle(self) -> Optional[bool]:
        if self._stop_signal or self._abort_signal:
            self._shared.com_if_ref_tracker.remove_user()
            if not self._abort_signal:
                self._finish_success()
            return False
        else:
            # We only should run the TM operation here
            self._shared.backend.tm_operation()
            # Poll TM every 400 ms for now
            time.sleep(self._locals.op_args)

    def __loop(self, op_code: WorkerOperationsCodes) -> bool:
        if op_code == WorkerOperationsCodes.ONE_QUEUE_MODE:
            should_return = self.__one_queue_mode_cycle()
            if should_return is not None:
                return should_return
        elif op_code == WorkerOperationsCodes.LISTEN_FOR_TM:
            should_return = self.__listener_cycle()
            if should_return is not None:
                return should_return
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

    def _abort(self, _args: any):
        self._abort_signal = True
