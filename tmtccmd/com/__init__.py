# -*- coding: utf-8 -*-
"""Communication module. Provides generic abstraction for communication and commonly used
concrete implementations."""
from abc import abstractmethod, ABC
from typing import Optional

from tmtccmd.tm import TelemetryListT


class ReceptionDecodeError(Exception):
    """Generic decode error which can also wrap the exception thrown by other libraries."""

    def __init__(self, msg: str, custom_exception: Optional[Exception]):
        super().__init__(msg)
        self.custom_exception = custom_exception


class SendError(Exception):
    """Generic send error which can also wrap the exception thrown by other libraries."""

    def __init__(self, msg: str, custom_exception: Optional[Exception]):
        super().__init__(msg)
        self.custom_exception = custom_exception


class ComInterface(ABC):
    """Generic form of a communication interface to separate communication logic from
    the underlying interface.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @abstractmethod
    def initialize(self, args: any = 0) -> any:
        """Perform initializations step which can not be done in constructor or which require
        returnvalues.
        """

    @abstractmethod
    def open(self, args: any = 0):
        """Opens the communication interface to allow communication.

        :return:
        """

    @abstractmethod
    def is_open(self) -> bool:
        """Can be used to check whether the communication interface is open. This is useful if
        opening a COM interface takes a longer time and is non-blocking
        """

    @abstractmethod
    def close(self, args: any = 0):
        """Closes the ComIF and releases any held resources (for example a Communication Port).

        :return:
        """

    @abstractmethod
    def send(self, data: bytes):
        """Send raw data.

        :raises SendError: Sending failed for some reason.
        """

    @abstractmethod
    def receive(self, parameters: any = 0) -> TelemetryListT:
        """Returns a list of received packets. The child class can use a separate thread to poll for
        the packets or use some other mechanism and container like a deque to store packets
        to be returned here.

        :param parameters:
        :raises ReceptionDecodeError: If the underlying COM interface uses encoding and
            decoding and the decoding fails, this exception will be returned.
        :return:
        """
        packet_list = []
        return packet_list

    @abstractmethod
    def data_available(self, timeout: float, parameters: any = 0) -> int:
        """Check whether TM packets are available.

        :param timeout: Can be used to block on available data if supported by the specific
            communication interface.
        :param parameters: Can be an arbitrary parameter.
        :raises ReceptionDecodeError: If the underlying COM interface uses encoding and
            decoding when determining the number of available packets, this exception can be
            thrown on decoding errors.
        :return: 0 if no data is available, number of packets otherwise.
        """
