import enum
from spacepackets.cfdp import GenericPduPacket
from spacepackets.cfdp.pdu import AbstractFileDirectiveBase


class InvalidPduForSourceHandler(Exception):
    def __init__(self, packet: AbstractFileDirectiveBase):
        self.packet = packet
        super().__init__(f"Invalid packet {self.packet} for source handler")


class PduIgnoredAtSourceReason(enum.IntEnum):
    # The received PDU can only be used for acknowledged mode.
    ACK_MODE_PACKET_INVALID_MODE = 0
    # Received a Finished PDU, but source handler is currently not expecting one.
    NOT_WAITING_FOR_FINISHED_PDU = 1
    # Received a ACK PDU, but source handler is currently not expecting one.
    NOT_WAITING_FOR_ACK = 2


class PduIgnoredForSource(Exception):
    def __init__(
        self,
        reason: PduIgnoredAtSourceReason,
        ignored_packet: AbstractFileDirectiveBase,
    ):
        self.ignored_packet = ignored_packet
        self.reason = reason
        super().__init__(f"ignored PDU packet at source handler: {reason!r}")


class InvalidPduForDestHandler(Exception):
    def __init__(self, packet: GenericPduPacket):
        self.packet = packet
        super().__init__(f"Invalid packet {self.packet} for source handler")


class PduIgnoredForDestReason(enum.IntEnum):
    FIRST_PACKET_NOT_METADATA_PDU = 0
    """First packet received was not a metadata PDU for the unacknowledged mode."""
    INVALID_MODE_FOR_ACKED_MODE_PACKET = 1
    """The received PDU can only be handled in acknowledged mode."""
    FIRST_PACKET_IN_ACKED_MODE_NOT_METADATA_NOT_EOF_NOT_FD = 2
    """For the acknowledged mode, the first packet that was received with
    no metadata received previously was not a File Data PDU or EOF PDU."""


class PduIgnoredForDest(Exception):
    def __init__(
        self, reason: PduIgnoredForDestReason, ignored_packet: GenericPduPacket
    ):
        self.ignored_packet = ignored_packet
        self.reason = reason
        super().__init__(f"ignored PDU packet at destination handler: {reason!r}")
