#!/usr/bin/env python3
"""This example shows a end-to-end transfer of a small file using the CFDP high level
components provided by the tmtccmd package."""
import copy
import logging
import os
import threading
import time
from logging import basicConfig
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from typing import Any

from spacepackets.cfdp import GenericPduPacket
from spacepackets.cfdp.defs import ChecksumType, ConditionCode, TransmissionMode
from spacepackets.cfdp.pdu import AbstractFileDirectiveBase
from spacepackets.util import ByteFieldU16

from tmtccmd.cfdp.defs import CfdpState, TransactionId
from tmtccmd.cfdp.handler.dest import DestHandler
from tmtccmd.cfdp.handler.source import SourceHandler
from tmtccmd.cfdp.mib import (
    DefaultFaultHandlerBase,
    IndicationCfg,
    LocalEntityCfg,
    RemoteEntityCfg,
    RemoteEntityCfgTable,
)
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.cfdp.user import (
    CfdpUserBase,
    FileSegmentRecvdParams,
    MetadataRecvParams,
    TransactionFinishedParams,
)
from tmtccmd.util.seqcnt import SeqCountProvider

SOURCE_ENTITY_ID = ByteFieldU16(1)
DEST_ENTITY_ID = ByteFieldU16(2)

FILE_CONTENT = "Hello World!\n"
FILE_SEGMENT_SIZE = len(FILE_CONTENT)
MAX_PACKET_LEN = 512
SOURCE_FILE = Path("/tmp/cfdp-test-source.txt")
DEST_FILE = Path("/tmp/cfdp-test-dest.txt")


_LOGGER = logging.getLogger()


REMOTE_CFG_FOR_SOURCE_ENTITY = RemoteEntityCfg(
    entity_id=SOURCE_ENTITY_ID,
    max_packet_len=MAX_PACKET_LEN,
    max_file_segment_len=FILE_SEGMENT_SIZE,
    closure_requested=True,
    crc_on_transmission=False,
    default_transmission_mode=TransmissionMode.UNACKNOWLEDGED,
    crc_type=ChecksumType.CRC_32,
    check_limit_provider=None,
)
REMOTE_CFG_FOR_DEST_ENTITY = copy.copy(REMOTE_CFG_FOR_SOURCE_ENTITY)
REMOTE_CFG_FOR_DEST_ENTITY.entity_id = DEST_ENTITY_ID

# These queues will be used to exchange PDUs between threads.
SOURCE_TO_DEST_QUEUE = Queue()
DEST_TO_SOURCE_QUEUE = Queue()


class CfdpFaultHandler(DefaultFaultHandlerBase):
    def notice_of_suspension_cb(self, cond: ConditionCode):
        _LOGGER.warn(f"Received Notice of Suspension with condition code {cond!r}")

    def notice_of_cancellation_cb(self, cond: ConditionCode):
        _LOGGER.warn(f"Received Notice of Cancellation with condition code {cond!r}")

    def abandoned_cb(self, cond: ConditionCode):
        _LOGGER.warn(f"Received Abandoned Fault with condition code {cond!r}")

    def ignore_cb(self, cond: ConditionCode):
        _LOGGER.warn(f"Received Ignored Fault with condition code {cond!r}")


class CfdpUser(CfdpUserBase):
    def __init__(self, base_str: str):
        self.base_str = base_str
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


def main():
    basicConfig(level=logging.INFO)
    if SOURCE_FILE.exists():
        os.remove(SOURCE_FILE)
    if DEST_FILE.exists():
        os.remove(DEST_FILE)
    with open(SOURCE_FILE, "w") as file:
        file.write(FILE_CONTENT)
    # Enable all indications.
    src_indication_cfg = IndicationCfg()
    src_fault_handler = CfdpFaultHandler()
    src_entity_cfg = LocalEntityCfg(
        SOURCE_ENTITY_ID, src_indication_cfg, src_fault_handler
    )
    # 16 bit sequence count for transactions.
    src_seq_count_provider = SeqCountProvider(16)
    src_user = CfdpUser("SRC ENTITY")
    source_handler = SourceHandler(src_entity_cfg, src_seq_count_provider, src_user)
    # Spawn a new thread and move the source handler there. This is scalable: If multiple number
    # of concurrent file operations are required, a new thread with a new source handler can
    # be spawned for each one.
    source_thread = threading.Thread(
        target=source_entity_handler, args=[source_handler]
    )

    # Enable all indications.
    dest_indication_cfg = IndicationCfg()
    dest_fault_handler = CfdpFaultHandler()
    dest_entity_cfg = LocalEntityCfg(
        DEST_ENTITY_ID, dest_indication_cfg, dest_fault_handler
    )
    dest_user = CfdpUser("DEST ENTITY")
    remote_cfg_table = RemoteEntityCfgTable()
    remote_cfg_table.add_config(REMOTE_CFG_FOR_SOURCE_ENTITY)
    dest_handler = DestHandler(dest_entity_cfg, dest_user, remote_cfg_table)
    # Spawn a new thread and move the destination handler there. This is scalable. One example
    # approach could be to keep a dictionary of active file copy operations, where the transaction
    # ID is the key. If a new Metadata PDU with a new transaction ID is detected, a new
    # destination handler in a new thread could be spawned to handle the file copy operation.
    dest_thread = threading.Thread(target=dest_entity_handler, args=[dest_handler])

    source_thread.start()
    dest_thread.start()
    source_thread.join()
    dest_thread.join()

    src_file_content = None
    with open(SOURCE_FILE) as file:
        src_file_content = file.read()
    dest_file_content = None
    with open(DEST_FILE) as file:
        dest_file_content = file.read()
    assert src_file_content == dest_file_content
    _LOGGER.info("Source and destination file content are equal. Deleting files.")
    if SOURCE_FILE.exists():
        os.remove(SOURCE_FILE)
    if DEST_FILE.exists():
        os.remove(DEST_FILE)
    _LOGGER.info("Done.")


def source_entity_handler(source_handler: SourceHandler):
    # This put request could in principle also be sent from something like a front end application.
    put_request = PutRequest(
        destination_id=DEST_ENTITY_ID,
        source_file=SOURCE_FILE,
        dest_file=DEST_FILE,
        trans_mode=TransmissionMode.UNACKNOWLEDGED,
        closure_requested=True,
    )
    no_packet_received = False
    print(f"SRC HANDLER: Inserting Put Request: {put_request}")
    with open(SOURCE_FILE) as file:
        file_content = file.read()
        print(f"File content of source file {SOURCE_FILE}: {file_content}")
    assert source_handler.put_request(put_request, REMOTE_CFG_FOR_DEST_ENTITY)
    while True:
        try:
            # We are getting the packets from a Queue here, they could for example also be polled
            # from a network.
            packet: AbstractFileDirectiveBase = DEST_TO_SOURCE_QUEUE.get(False)
            source_handler.insert_packet(packet)
            no_packet_received = False
        except Empty:
            no_packet_received = True
        fsm_result = source_handler.state_machine()
        no_packet_sent = False
        if fsm_result.states.packets_ready:
            next_packet = source_handler.get_next_packet()
            # Send all packets which need to be sent.
            while next_packet is not None:
                SOURCE_TO_DEST_QUEUE.put(next_packet.pdu)
                next_packet = source_handler.get_next_packet()
            no_packet_sent = False
        else:
            no_packet_sent = True
        if no_packet_received and no_packet_sent:
            time.sleep(0.5)
        # Transaction done
        if fsm_result.states.state == CfdpState.IDLE:
            _LOGGER.info("Source entity operation done.")
            break


def dest_entity_handler(dest_handler: DestHandler):
    first_packet = True
    no_packet_received = False
    while True:
        try:
            packet: GenericPduPacket = SOURCE_TO_DEST_QUEUE.get(False)
            dest_handler.insert_packet(packet)
            no_packet_received = False
            if first_packet:
                first_packet = False
        except Empty:
            no_packet_received = True
        fsm_result = dest_handler.state_machine()
        if fsm_result.states.packets_ready:
            DEST_TO_SOURCE_QUEUE.put(fsm_result.pdu_holder.pdu)
            dest_handler.confirm_packet_sent_advance_fsm()
            no_packet_sent = False
        else:
            no_packet_sent = True
        if no_packet_received and no_packet_sent:
            time.sleep(0.5)
        # Transaction done
        if not first_packet and fsm_result.states.state == CfdpState.IDLE:
            _LOGGER.info("Destination entity operation done.")
            break
    with open(DEST_FILE) as file:
        file_content = file.read()
        print(f"File content of destination file {DEST_FILE}: {file_content}")


if __name__ == "__main__":
    main()
