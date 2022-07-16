from dataclasses import dataclass

from spacepackets.cfdp.pdu import PduHolder

from tmtccmd.logging import get_console_logger
from tmtccmd.util import ProvidesSeqCount
from tmtccmd.cfdp import LocalEntityCfg, RemoteEntityCfgTable, CfdpUserBase
from tmtccmd.cfdp.request import CfdpRequestWrapper, PutRequest
from tmtccmd.cfdp.defs import CfdpStates, CfdpRequestType
from .defs import NoRemoteEntityCfgFound, BusyError

from .dest import DestStateWrapper
from .source import SourceHandler, SourceStateWrapper, FsmResult
from .source import TransactionStep as SourceTransactionStep
from .dest import TransactionStep as DestTransactionStep

LOGGER = get_console_logger()


@dataclass
class StateWrapper:
    source_handler_state = SourceStateWrapper()
    dest_handler_state = DestStateWrapper()


class CfdpResult:
    def __init__(self):
        pass


class CfdpHandler:
    def __init__(
        self,
        local_cfg: LocalEntityCfg,
        remote_cfg: RemoteEntityCfgTable,
        seq_num_provider: ProvidesSeqCount,
        cfdp_user: CfdpUserBase,
    ):
        """

        :param local_cfg: Local entity configuration
        :param remote_cfg: Configuration table for remote entities
        :param cfdp_user: CFDP user which will receive indication messages and which also contains
            the virtual filestore implementation
        """
        # The ID is going to be constant after initialization, store in separately
        self.id = local_cfg.local_entity_id
        self.cfg = local_cfg
        self.remote_cfg_table = remote_cfg
        self.cfdp_user = cfdp_user
        self._tx_handler = SourceHandler(self.cfg, seq_num_provider, cfdp_user)
        self.state = StateWrapper()
        self.state.source_handler_state = self._tx_handler.states
        self._request_wrapper = CfdpRequestWrapper(None)
        self._next_reception_pdu_wrapper = PduHolder(None)
        self._cfdp_result = CfdpResult()

    def state_machine(self) -> CfdpResult:
        """Perform the CFDP state machine. Primary function to call to generate new PDUs to send
        and to advance the internal state machine which also issues indications to the
        CFDP user.

        :raises SequenceNumberOverflow: Overflow of sequence number occurred. In this case, the
            number will be reset but no operation will occur and the state machine needs
            to be called again
        :raises NoRemoteEntityCfgFound: If no remote entity configuration for a given destination
            ID was found
        """
        if self.state != CfdpStates.IDLE:
            self._handle_transfer_state_machine()
            pass
        return self._cfdp_result

    def _handle_transfer_state_machine(self):
        if self._request_wrapper.request == CfdpRequestType.PUT:
            self._tx_handler.state_machine()

    def reset_transfer_state(self):
        pass
        # TODO: Implement
        # self.state.transfer_state = SorceState.IDLE
        # self._transfer_params.reset()

    def _prepare_finish_pdu(self):
        # TODO: Implement
        pass

    def pass_packet(self, raw_tm_packet: bytes):
        # TODO: Packet Handler
        pass

    @property
    def transfer_packet_ready(self):
        if self._tx_handler.pdu_holder.base is not None:
            return True
        return False

    @property
    def reception_packet_ready(self):
        if self._next_reception_pdu_wrapper.base is not None:
            return True
        return False

    @property
    def transfer_packet_wrapper(self) -> PduHolder:
        """Yield the next packet required to transfer a file"""
        return self._tx_handler.pdu_holder

    @property
    def reception_packet_wrapper(self) -> PduHolder:
        """Yield the next packed required to receive a file"""
        return self._next_reception_pdu_wrapper

    def start_put_request(self, put_request: PutRequest):
        """A put request initiates a copy procedure. For now, only one put request at a time
        is allowed"""
        if self.state.source_handler_state != CfdpStates.IDLE:
            raise BusyError(f"Currently in {self.state}, can not handle put request")
        self._request_wrapper.base = put_request
        remote_cfg = self.remote_cfg_table.get_remote_entity(
            put_request.cfg.destination_id
        )
        if remote_cfg is None:
            raise NoRemoteEntityCfgFound(put_request.cfg.destination_id)
        self._tx_handler.start_transaction(
            remote_cfg=remote_cfg, wrapper=self._request_wrapper
        )
