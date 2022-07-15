from __future__ import annotations

import time
from typing import Optional
from datetime import timedelta


def time_ms() -> int:
    return round(time.time() * 1000)


class Countdown:
    def __init__(self, init_timeout: Optional[timedelta]):
        if init_timeout is not None:
            self._timeout_ms = int(init_timeout / timedelta(milliseconds=1))
            self._start_time_ms = time_ms()
        else:
            self._timeout_ms = 0
            self._start_time_ms = 0

    @classmethod
    def from_millis(cls, timeout_ms: int) -> Countdown:
        return cls(timedelta(milliseconds=timeout_ms))

    @property
    def timeout(self):
        return self._timeout_ms

    @timeout.setter
    def timeout(self, timeout: timedelta):
        self._timeout_ms = round(timeout / timedelta(milliseconds=1))

    def timed_out(self) -> bool:
        if round(time_ms() - self._start_time_ms) >= self._timeout_ms:
            return True
        else:
            return False

    def busy(self) -> bool:
        return not self.timed_out()

    def reset(self, new_timeout: Optional[timedelta] = None):
        if new_timeout is not None:
            self.timeout = new_timeout
        self.start()

    def start(self):
        self._start_time_ms = time_ms()

    def time_out(self):
        self._start_time_ms = 0

    def rem_time(self) -> timedelta:
        end_time = self._start_time_ms + self._timeout_ms
        current = time_ms()
        if end_time < current:
            return timedelta()
        return timedelta(milliseconds=end_time - current)

    def __repr__(self):
        return f"{self.__class__.__name__}(init_timeout={timedelta(milliseconds=self._timeout_ms)})"

    def __str__(self):
        return (
            f"{self.__class__.__class__} with {timedelta(milliseconds=self._timeout_ms)} "
            f"ms timeout, {self.rem_time()} time remaining"
        )
