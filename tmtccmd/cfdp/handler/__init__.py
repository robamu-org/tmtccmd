from dataclasses import dataclass
from typing import Sequence, Optional, Tuple

import deprecation

from spacepackets import SpacePacket, SpacePacketHeader, PacketType
from spacepackets.cfdp import GenericPduPacket, PduType, DirectiveType, PduFactory
from spacepackets.cfdp.pdu import PduHolder

from tmtccmd.util import ProvidesSeqCount
from tmtccmd.cfdp import (
    LocalEntityCfg,
    RemoteEntityCfgTable,
    CfdpUserBase,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.cfdp.defs import CfdpStates
from tmtccmd.version import get_version
from .defs import NoRemoteEntityCfgFound, BusyError

from .dest import DestStateWrapper
from .dest import DestHandler
from .source import SourceHandler, SourceStateWrapper, FsmResult
from .source import TransactionStep as SourceTransactionStep
from .dest import TransactionStep as DestTransactionStep
from .common import PacketDestination, get_packet_destination


@dataclass
class StateWrapper:
    source_handler_state = SourceStateWrapper()
    dest_handler_state = DestStateWrapper()


class CfdpHandler:
    """Wrapper class which wraps both the :py:class:`tmtccmd.cfdp.handler.source.SourceHandler` and
    :py:class:`tmtccmd.cfdp.handler.dest.DestHandler` in a sensible way.

    If you have special requirements, for example you want to spawn a new destination handler
    for each file copy transfer to allow multiple consecutive file transfers, it might be a good
    idea to write a custom wrapper."""

    def __init__(
        self,
        cfg: LocalEntityCfg,
        user: CfdpUserBase,
        seq_cnt_provider: ProvidesSeqCount,
        remote_cfgs: Sequence[RemoteEntityCfg],
    ):
        self.remote_cfg_table = RemoteEntityCfgTable()
        self.remote_cfg_table.add_configs(remote_cfgs)
        self.dest_handler = DestHandler(cfg, user, self.remote_cfg_table)
        self.source_handler = SourceHandler(cfg, seq_cnt_provider, user)

    def put_request(self, request: PutRequest):
        if not self.remote_cfg_table.get_cfg(request.destination_id):
            raise ValueError(
                f"No remote CFDP config found for entity ID {request.destination_id}"
            )
        self.source_handler.put_request(
            request, self.remote_cfg_table.get_cfg(request.destination_id)
        )

    def pull_next_source_packet(self) -> Optional[PduHolder]:
        res = self.source_handler.state_machine()
        if res.states.packet_ready:
            return self.source_handler.pdu_holder
        return None

    def pull_next_dest_packet(self) -> Optional[PduHolder]:
        res = self.dest_handler.state_machine()
        if res.states.packet_ready:
            return self.dest_handler.pdu_holder
        return None

    def __iter__(self):
        return self

    def __next__(self) -> Tuple[Optional[PduHolder], Optional[PduHolder]]:
        """The iterator for this class will returns a tuple of optional PDUs wrapped b a
        :py:class:`PduHolder`.

        :return: Can be a tuple where the first entry can hold a source packet and the second entry
            can be a destination packet. If both packets are None, a StopIteration will be raised.
        """
        next_source_packet = self.pull_next_source_packet()
        next_dest_packet = self.pull_next_dest_packet()
        if not next_dest_packet and not next_source_packet:
            raise StopIteration
        return next_source_packet, next_dest_packet

    def put_request_pending(self) -> bool:
        return self.source_handler.states.state != CfdpStates.IDLE

    def confirm_dest_packet_sent(self):
        self.dest_handler.confirm_packet_sent_advance_fsm()

    def confirm_source_packet_sent(self):
        self.source_handler.confirm_packet_sent_advance_fsm()

    @deprecation.deprecated(
        deprecated_in="6.0.0rc0",
        current_version=get_version(),
        details="Use insert_packet instead",
    )
    def pass_packet(self, packet: GenericPduPacket):
        self.insert_packet(packet)

    def insert_packet(self, packet: GenericPduPacket):
        """This function routes the packets based on PDU type and directive type if applicable.

        The routing is based on section 4.5 of the CFDP standard which specifies the PDU forwarding
        procedure."""
        if get_packet_destination(packet) == PacketDestination.DEST_HANDLER:
            self.dest_handler.insert_packet(packet)
        elif get_packet_destination(packet) == PacketDestination.SOURCE_HANDLER:
            self.source_handler.insert_packet(packet)  # type: ignore


class CfdpInCcsdsHandler:
    """Wrapper helper type used to wrap PDU packets into CCSDS packets and to extract PDU
    packets from CCSDS packets.

    :param cfg: Local CFDP entity configuration.
    :param user: User wrapper. This contains the indication callback implementations and the
        virtual filestore implementation.
    :param cfdp_seq_cnt_provider: Every CFDP file transfer has a transaction sequence number.
        This provider is used to retrieve that sequence number.
    :param ccsds_seq_cnt_provider: Each CFDP PDU is wrapped into a CCSDS space packet, and each
        space packet has a dedicated sequence count. This provider is used to retrieve the
        sequence count.
    :param ccsds_apid: APID to use for the CCSDS space packet header wrapped around each PDU.
        This is important so that the OBSW can distinguish between regular PUS packets and
        CFDP packets."""

    def __init__(
        self,
        cfg: LocalEntityCfg,
        user: CfdpUserBase,
        remote_cfgs: Sequence[RemoteEntityCfg],
        ccsds_apid: int,
        cfdp_seq_cnt_provider: ProvidesSeqCount,
        ccsds_seq_cnt_provider: ProvidesSeqCount,
    ):
        self.cfdp_handler = CfdpHandler(cfg, user, cfdp_seq_cnt_provider, remote_cfgs)
        self.ccsds_seq_cnt_provider = ccsds_seq_cnt_provider
        self.ccsds_apid = ccsds_apid

    def put_request_pending(self):
        return self.cfdp_handler.put_request_pending()

    def state_machine(self):
        self.source_handler.state_machine()
        self.dest_handler.state_machine()

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use state_machine instead",
    )
    def fsm(self):
        self.state_machine()

    @property
    def source_handler(self):
        return self.cfdp_handler.source_handler

    @property
    def dest_handler(self):
        return self.cfdp_handler.dest_handler

    def pull_next_source_packet(self) -> Optional[Tuple[PduHolder, SpacePacket]]:
        """Retrieves the next PDU to send and wraps it into a space packet"""
        next_packet = self.cfdp_handler.pull_next_source_packet()
        if next_packet is None:
            return next_packet
        sp_header = SpacePacketHeader(
            packet_type=PacketType.TC,
            apid=self.ccsds_apid,
            seq_count=self.ccsds_seq_cnt_provider.get_and_increment(),
            data_len=next_packet.packet_len - 1,
        )
        return next_packet, SpacePacket(sp_header, None, next_packet.pack())

    def pull_next_dest_packet(self) -> Optional[Tuple[PduHolder, SpacePacket]]:
        """Retrieves the next PDU to send and wraps it into a space packet"""
        next_packet = self.cfdp_handler.pull_next_dest_packet()
        if next_packet is None:
            return next_packet
        sp_header = SpacePacketHeader(
            packet_type=PacketType.TC,
            apid=self.ccsds_apid,
            seq_count=self.ccsds_seq_cnt_provider.get_and_increment(),
            data_len=next_packet.packet_len - 1,
        )
        return next_packet, SpacePacket(sp_header, None, next_packet.pack())

    def confirm_dest_packet_sent(self):
        self.cfdp_handler.confirm_dest_packet_sent()

    def confirm_source_packet_sent(self):
        self.cfdp_handler.confirm_source_packet_sent()

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use insert_space_packet instead",
    )
    def pass_space_packet(self, space_packet: SpacePacket):
        self.insert_space_packet(space_packet)

    def insert_space_packet(self, space_packet: SpacePacket) -> bool:
        if space_packet.user_data is None:
            raise ValueError(
                "space packet is empty, expected packet containing a CFDP PDU"
            )
        # Unwrap the user data and pass it to the handler
        pdu_raw = space_packet.user_data
        pdu_base = PduFactory.from_raw(pdu_raw)
        if pdu_base:
            self.insert_pdu_packet(pdu_base)
            return True
        return False

    def insert_pdu_packet(self, pdu: GenericPduPacket):
        self.cfdp_handler.insert_packet(pdu)

    @deprecation.deprecated(
        deprecated_in="6.0.0rc1",
        current_version=get_version(),
        details="Use insert_pdu_packet instead",
    )
    def pass_pdu_packet(self, pdu_base: GenericPduPacket):
        self.insert_pdu_packet(pdu_base)

    def __iter__(self):
        return self

    def __next__(
        self,
    ) -> (
        Optional[Tuple[PduHolder, SpacePacket]],
        Optional[Tuple[PduHolder, SpacePacket]],
    ):
        """The iterator for this class will returns a tuple of optional PDUs wrapped b a
        :py:class:`PduHolder`.

        :return: Can be a tuple where the first entry can hold a source packet and the second entry
            can be a destination packet. If both packets are None, a StopIteration will be raised.
        """
        next_source_tuple = self.pull_next_source_packet()
        next_dest_tuple = self.pull_next_dest_packet()
        if not next_source_tuple and not next_dest_tuple:
            raise StopIteration
        return next_source_tuple, next_dest_tuple
