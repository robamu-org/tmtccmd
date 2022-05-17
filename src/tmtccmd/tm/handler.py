from tmtccmd.tm.definitions import TmTypes


class TmHandler:
    def __init__(self, tm_type: TmTypes):
        self._tm_type = tm_type

    def get_type(self):
        return self._tm_type
