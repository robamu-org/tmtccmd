import time
from typing import Optional


class Countdown:
    def __init__(self, init_timeout_secs: Optional[float]):
        if init_timeout_secs is not None:
            self._timeout = init_timeout_secs
        else:
            self._timeout = 0
        self._start_time = time.time()

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: float):
        self._timeout = timeout

    def timed_out(self) -> bool:
        if time.time() - self._start_time > self._timeout:
            return True
        else:
            return False

    def busy(self) -> bool:
        return not self.timed_out()

    def reset(self, new_timeout: Optional[float] = None):
        if new_timeout is not None:
            self.timeout = new_timeout
        else:
            self.timeout = self._timeout
        self.start()

    def start(self):
        self._start_time = time.time()

    def time_out(self):
        self._start_time = time.time() - self._timeout

    def rem_time(self) -> float:
        end_time = self._start_time + self._timeout
        current = time.time()
        if end_time < current:
            return 0
        return end_time - current
