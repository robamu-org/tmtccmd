from typing import Any, Tuple, Optional, List
from multiprocessing import Queue
from queue import Empty
from threading import Thread
import time
import select
import socket
import logging
import copy

from datetime import timedelta
from spacepackets.cfdp import GenericPduPacket
from spacepackets.cfdp.pdu import AbstractFileDirectiveBase
from spacepackets.cfdp import (
    TransactionId,
    ConditionCode,
    TransmissionMode,
    ChecksumType,
)
from spacepackets.cfdp.tlv import (
    ProxyMessageType,
    MessageToUserTlv,
    OriginatingTransactionId,
)
from spacepackets.util import UnsignedByteField, ByteFieldU16
from tmtccmd.cfdp.user import (
    CfdpUserBase,
    FileSegmentRecvdParams,
    MetadataRecvParams,
    TransactionFinishedParams,
)
from tmtccmd.cfdp.exceptions import InvalidDestinationId

from tmtccmd.cfdp import get_packet_destination, PacketDestination
from tmtccmd.util.countdown import Countdown
from tmtccmd.cfdp.mib import (
    CheckTimerProvider,
    DefaultFaultHandlerBase,
    EntityType,
    IndicationCfg,
    RemoteEntityCfg,
)
from tmtccmd.cfdp.handler import SourceHandler, DestHandler, CfdpState
from tmtccmd.cfdp import PutRequest
from spacepackets.cfdp.pdu import PduFactory, PduHolder

_LOGGER = logging.getLogger()

LOCAL_ENTITY_ID = ByteFieldU16(1)
REMOTE_ENTITY_ID = ByteFieldU16(2)
# Enable all indications for both local and remote entity.
INDICATION_CFG = IndicationCfg()

FILE_CONTENT = "Hello World!\n"
FILE_SEGMENT_SIZE = 256
MAX_PACKET_LEN = 512

REMOTE_CFG_OF_LOCAL_ENTITY = RemoteEntityCfg(
    entity_id=LOCAL_ENTITY_ID,
    max_packet_len=MAX_PACKET_LEN,
    max_file_segment_len=FILE_SEGMENT_SIZE,
    closure_requested=True,
    crc_on_transmission=False,
    default_transmission_mode=TransmissionMode.ACKNOWLEDGED,
    crc_type=ChecksumType.CRC_32,
)

REMOTE_CFG_OF_REMOTE_ENTITY = copy.copy(REMOTE_CFG_OF_LOCAL_ENTITY)
REMOTE_CFG_OF_REMOTE_ENTITY.entity_id = REMOTE_ENTITY_ID

LOCAL_PORT = 5111
REMOTE_PORT = 5222


class CfdpFaultHandler(DefaultFaultHandlerBase):
    def __init__(self, base_str: str):
        self.base_str = base_str

    def notice_of_suspension_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"{self.base_str}: Received Notice of Suspension for transaction {transaction_id!r} "
            f"with condition code {cond!r}. Progress: {progress}"
        )

    def notice_of_cancellation_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"{self.base_str}: Received Notice of Cancellation for transaction {transaction_id!r} "
            f"with condition code {cond!r}. Progress: {progress}"
        )

    def abandoned_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"{self.base_str}: Abandoned fault for transaction {transaction_id!r} "
            f"with condition code {cond!r}. Progress: {progress}"
        )

    def ignore_cb(
        self, transaction_id: TransactionId, cond: ConditionCode, progress: int
    ):
        _LOGGER.warning(
            f"{self.base_str}: Ignored fault for transaction {transaction_id!r} "
            f"with condition code {cond!r}. Progress: {progress}"
        )


class CfdpUser(CfdpUserBase):
    def __init__(self, base_str: str, put_req_queue: Queue):
        self.base_str = base_str
        self.put_req_queue = put_req_queue
        self.active_proxy_put_reqs = []
        super().__init__()

    def transaction_indication(self, transaction_id: TransactionId):
        """This indication is used to report the transaction ID to the CFDP user"""
        _LOGGER.info(f"{self.base_str}: Transaction.indication for {transaction_id}")

    def eof_sent_indication(self, transaction_id: TransactionId):
        _LOGGER.info(f"{self.base_str}: EOF-Sent.indication for {transaction_id}")

    def transaction_finished_indication(self, params: TransactionFinishedParams):
        _LOGGER.info(
            f"{self.base_str}: Transaction-Finished.indication for {params.transaction_id}."
        )

    def metadata_recv_indication(self, params: MetadataRecvParams):
        _LOGGER.info(
            f"{self.base_str}: Metadata-Recv.indication for {params.transaction_id}."
        )
        if params.msgs_to_user is not None:
            self._handle_msgs_to_user(params.msgs_to_user)

    def _handle_msgs_to_user(
        self, transaction_id: TransactionId, msgs_to_user: List[MessageToUserTlv]
    ):
        for msg_to_user in msgs_to_user:
            if msg_to_user.is_reserved_cfdp_message():
                # TODO: Add support for all other reserved message types.
                reserved_cfdp_msg = msg_to_user.to_reserved_msg_tlv()
                if (
                    reserved_cfdp_msg.is_cfdp_proxy_operation()
                    and reserved_cfdp_msg.get_cfdp_proxy_message_type()
                    == ProxyMessageType.PUT_REQUEST
                ):
                    put_req_params = reserved_cfdp_msg.get_proxy_put_request_params()
                    _LOGGER.info(f"Received Proxy Put Request: {put_req_params}")
                    assert put_req_params is not None
                    put_req = PutRequest(
                        destination_id=put_req_params.dest_entity_id,
                        source_file=put_req_params.source_file_as_path,
                        dest_file=put_req_params.dest_file_as_path,
                        trans_mode=None,
                        closure_requested=None,
                        msgs_to_user=[OriginatingTransactionId(transaction_id)],
                    )
                    self.active_proxy_put_reqs.append(put_req)
                    self.put_req_queue.put(put_req)

    def file_segment_recv_indication(self, params: FileSegmentRecvdParams):
        _LOGGER.info(
            f"{self.base_str}: File-Segment-Recv.indication for {params.transaction_id}."
        )

    def report_indication(self, transaction_id: TransactionId, status_report: Any):
        # TODO: p.28 of the CFDP standard specifies what information the status report parameter
        #       could contain. I think it would be better to not hardcode the type of the status
        #       report here, but something like Union[any, CfdpStatusReport] with CfdpStatusReport
        #       being an implementation which supports all three information suggestions would be
        #       nice
        pass

    def suspended_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode
    ):
        _LOGGER.info(
            f"{self.base_str}: Suspended.indication for {transaction_id} | Condition Code: {cond_code}"
        )

    def resumed_indication(self, transaction_id: TransactionId, progress: int):
        _LOGGER.info(
            f"{self.base_str}: Resumed.indication for {transaction_id} | Progress: {progress} bytes"
        )

    def fault_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        _LOGGER.info(
            f"{self.base_str}: Fault.indication for {transaction_id} | Condition Code: {cond_code} | "
            f"Progress: {progress} bytes"
        )

    def abandoned_indication(
        self, transaction_id: TransactionId, cond_code: ConditionCode, progress: int
    ):
        _LOGGER.info(
            f"{self.base_str}: Abandoned.indication for {transaction_id} | Condition Code: {cond_code} |"
            f" Progress: {progress} bytes"
        )

    def eof_recv_indication(self, transaction_id: TransactionId):
        _LOGGER.info(f"{self.base_str}: EOF-Recv.indication for {transaction_id}")


class CustomCheckTimerProvider(CheckTimerProvider):
    def provide_check_timer(
        self,
        local_entity_id: UnsignedByteField,
        remote_entity_id: UnsignedByteField,
        entity_type: EntityType,
    ) -> Countdown:
        return Countdown(timedelta(seconds=5.0))


class UdpServer(Thread):
    def __init__(
        self,
        sleep_time: float,
        addr: Tuple[str, int],
        remote: Tuple[str, int],
        tx_queue: Queue,
        source_entity_rx_queue: Queue,
        dest_entity_rx_queue: Queue,
    ):
        super().__init__()
        self.sleep_time = sleep_time
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.addr = addr
        self.udp_socket.bind(addr)
        self.remote = remote
        self.tm_queue = tx_queue
        self.source_entity_queue = source_entity_rx_queue
        self.dest_entity_queue = dest_entity_rx_queue

    def run(self):
        _LOGGER.info(f"Starting UDP server on {self.addr}")
        while True:
            self.periodic_operation()
            time.sleep(self.sleep_time)

    def periodic_operation(self) -> bool:
        while True:
            next_packet = self.poll_next_udp_packet()
            if next_packet is None:
                break
            # Perform PDU routing.
            packet_dest = get_packet_destination(next_packet.pdu)
            if packet_dest == PacketDestination.DEST_HANDLER:
                self.dest_entity_queue.put(next_packet.pdu)
            elif packet_dest == PacketDestination.SOURCE_HANDLER:
                self.source_entity_queue.put(next_packet.pdu)
        self.send_packets()

    def poll_next_udp_packet(self) -> Optional[PduHolder]:
        ready = select.select([self.udp_socket], [], [], 0)
        if ready[0]:
            data, self.last_sender = self.udp_socket.recvfrom(4096)
            return PduFactory.from_raw_to_holder(data)
        return None

    def send_packets(self) -> bool:
        while True:
            try:
                next_tm = self.tm_queue.get(False)
                if not isinstance(next_tm, bytes) and not isinstance(
                    next_tm, bytearray
                ):
                    _LOGGER.error(
                        f"UDP server can only sent bytearray, received {next_tm}"
                    )
                    continue
                self.udp_socket.sendto(next_tm, self.remote)
            except Empty:
                break


class SourceEntityHandler(Thread):
    def __init__(
        self,
        base_str: str,
        verbose_level: int,
        source_handler: SourceHandler,
        put_req_queue: Queue,
        source_entity_queue: Queue,
        tm_queue: Queue,
    ):
        super().__init__()
        self.base_str = base_str
        self.verbose_level = verbose_level
        self.source_handler = source_handler
        self.put_req_queue = put_req_queue
        self.source_entity_queue = source_entity_queue
        self.tm_queue = tm_queue

    def _idle_handling(self) -> bool:
        try:
            put_req: PutRequest = self.put_req_queue.get(False)
            _LOGGER.info(f"{self.base_str}: Handling Put Request: {put_req}")
            if put_req.destination_id not in [LOCAL_ENTITY_ID, REMOTE_ENTITY_ID]:
                _LOGGER.warning(
                    f"can only handle put requests target towards {REMOTE_ENTITY_ID} or "
                    f"{LOCAL_ENTITY_ID}"
                )
            else:
                self.source_handler.put_request(put_req)
        except Empty:
            return False

    def _busy_handling(self):
        # We are getting the packets from a Queue here, they could for example also be polled
        # from a network.
        no_packet_received = True
        try:
            # We are getting the packets from a Queue here, they could for example also be polled
            # from a network.
            packet: AbstractFileDirectiveBase = self.source_entity_queue.get(False)
            try:
                self.source_handler.insert_packet(packet)
            except InvalidDestinationId as e:
                _LOGGER.warning(
                    f"invalid destination ID {e.found_dest_id} on packet {packet}, expected "
                    f"{e.expected_dest_id}"
                )
            no_packet_received = False
        except Empty:
            no_packet_received = True
        fsm_result = self.source_handler.state_machine()
        no_packet_sent = False
        if fsm_result.states.num_packets_ready > 0:
            while fsm_result.states.num_packets_ready > 0:
                next_pdu_wrapper = self.source_handler.get_next_packet()
                assert next_pdu_wrapper is not None
                if self.verbose_level >= 1:
                    _LOGGER.debug(
                        f"{self.base_str}: Sending packet {next_pdu_wrapper.pdu}"
                    )
                # Send all packets which need to be sent.
                self.tm_queue.put(next_pdu_wrapper.pack())
            no_packet_sent = False
        else:
            no_packet_sent = True
        # If there is no work to do, put the thread to sleep.
        if no_packet_received and no_packet_sent:
            return False

    def run(self):
        _LOGGER.info(f"Starting {self.base_str}")
        while True:
            if self.source_handler.state == CfdpState.IDLE:
                if not self._idle_handling():
                    time.sleep(0.2)
                    continue
            if self.source_handler.state == CfdpState.BUSY:
                if not self._busy_handling():
                    time.sleep(0.2)


class DestEntityHandler(Thread):
    def __init__(
        self,
        base_str: str,
        verbose_level: int,
        dest_handler: DestHandler,
        dest_entity_queue: Queue,
        tm_queue: Queue,
    ):
        super().__init__()
        self.base_str = base_str
        self.verbose_level = verbose_level
        self.dest_handler = dest_handler
        self.dest_entity_queue = dest_entity_queue
        self.tm_queue = tm_queue

    def run(self):
        _LOGGER.info(
            f"Starting {self.base_str}. Local ID {self.dest_handler.cfg.local_entity_id}"
        )
        first_packet = True
        no_packet_received = False
        while True:
            try:
                packet: GenericPduPacket = self.dest_entity_queue.get(False)
                self.dest_handler.insert_packet(packet)
                no_packet_received = False
                if first_packet:
                    first_packet = False
            except Empty:
                no_packet_received = True
            fsm_result = self.dest_handler.state_machine()
            if fsm_result.states.num_packets_ready > 0:
                no_packet_sent = False
                while fsm_result.states.num_packets_ready > 0:
                    next_pdu_wrapper = self.dest_handler.get_next_packet()
                    assert next_pdu_wrapper is not None
                    if self.verbose_level >= 1:
                        _LOGGER.debug(
                            f"REMOTE DEST ENTITY: Sending packet {next_pdu_wrapper.pdu}"
                        )
                    self.tm_queue.put(next_pdu_wrapper.pack())
            else:
                no_packet_sent = True
            # If there is no work to do, put the thread to sleep.
            if no_packet_received and no_packet_sent:
                time.sleep(0.5)
