from __future__ import annotations

from datetime import timedelta

from tmtccmd.tmtc.ccsds_seq_sender import SenderMode, SeqResultWrapper

from .base import BackendRequest, ModeWrapper


class BackendState:
    def __init__(
        self,
        mode_wrapper: None | ModeWrapper = None,
        req: BackendRequest = BackendRequest.NONE,
    ):
        if mode_wrapper is None:
            mode_wrapper = ModeWrapper()
        self._mode_wrapper = mode_wrapper
        self._req = req
        self._recommended_delay = timedelta()
        self._sender_res = SeqResultWrapper(SenderMode.DONE)

    @property
    def next_delay(self):
        return self._recommended_delay

    @property
    def request(self):
        return self._req

    @property
    def sender_res(self):
        return self._sender_res

    @property
    def tc_mode(self):
        return self._mode_wrapper.tc_mode

    @property
    def tm_mode(self):
        return self._mode_wrapper.tm_mode

    @property
    def mode_wrapper(self):
        return self._mode_wrapper
