from abc import abstractmethod


class BackendBase:
    @abstractmethod
    def initialize(self):
        """Initialize the backend. Raise RuntimeError or ValueError on failure"""

    @abstractmethod
    def start_listener(self, perform_op_immediately: bool):
        """Start the backend. Raise RuntimeError on failure"""

    @abstractmethod
    def set_mode(self, mode: int):
        """Set backend mode
        :param mode:
        :return:
        """
