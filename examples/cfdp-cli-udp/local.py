#!/usr/bin/env python3
"""This component simulates the local component."""
import argparse
import logging
from logging import basicConfig
from multiprocessing import Queue


from common import (
    INDICATION_CFG,
    LOCAL_ENTITY_ID,
    REMOTE_ENTITY_ID,
    REMOTE_CFG_OF_REMOTE_ENTITY,
    LOCAL_PORT,
    REMOTE_PORT,
    CfdpFaultHandler,
    CfdpUser,
    CustomCheckTimerProvider,
    DestEntityHandler,
    SourceEntityHandler,
    UdpServer,
)

from tmtccmd.cfdp.handler.dest import DestHandler
from tmtccmd.cfdp.handler.source import SourceHandler
from tmtccmd.cfdp.mib import (
    LocalEntityCfg,
    RemoteEntityCfgTable,
)
from tmtccmd.config.args import (
    add_cfdp_procedure_arguments,
    cfdp_args_to_cfdp_params,
    CfdpParams,
)
from tmtccmd.config.cfdp import generic_cfdp_params_to_put_request
from tmtccmd.util.seqcnt import SeqCountProvider

_LOGGER = logging.getLogger()

BASE_STR_SRC = "LOCAL SRC"
BASE_STR_DEST = "LOCAL DEST"

# This queue is used to send put requests.
PUT_REQ_QUEUE = Queue()
# All telecommands which should go to the source handler should be put into this queue by
# the UDP server.
SOURCE_ENTITY_QUEUE = Queue()
# All telecommands which should go to the destination handler should be put into this queue by
# the UDP server.
DEST_ENTITY_QUEUE = Queue()
# All telemetry which should be sent to the remote entity is put into this queue and will then
# be sent by the UDP server.
TM_QUEUE = Queue()


def main():
    parser = argparse.ArgumentParser(prog="CFDP Local Entity Application")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    add_cfdp_procedure_arguments(parser)
    args = parser.parse_args()
    if args.verbose == 0:
        logging_level = logging.INFO
    elif args.verbose >= 1:
        logging_level = logging.DEBUG
    if args.source is not None and args.target is not None:
        # Generate a put request from the CLI arguments.
        cfdp_params = CfdpParams()
        cfdp_args_to_cfdp_params(args, cfdp_params)
        put_req = generic_cfdp_params_to_put_request(
            cfdp_params, LOCAL_ENTITY_ID, REMOTE_ENTITY_ID, LOCAL_ENTITY_ID
        )
        PUT_REQ_QUEUE.put(put_req)

    basicConfig(level=logging_level)

    remote_cfg_table = RemoteEntityCfgTable()
    remote_cfg_table.add_config(REMOTE_CFG_OF_REMOTE_ENTITY)

    src_fault_handler = CfdpFaultHandler(BASE_STR_SRC)
    # 16 bit sequence count for transactions.
    src_seq_count_provider = SeqCountProvider(16)
    src_user = CfdpUser(BASE_STR_SRC, PUT_REQ_QUEUE)
    check_timer_provider = CustomCheckTimerProvider()
    source_handler = SourceHandler(
        cfg=LocalEntityCfg(LOCAL_ENTITY_ID, INDICATION_CFG, src_fault_handler),
        seq_num_provider=src_seq_count_provider,
        remote_cfg_table=remote_cfg_table,
        user=src_user,
        check_timer_provider=check_timer_provider,
    )
    source_entity_task = SourceEntityHandler(
        BASE_STR_SRC,
        logging_level,
        source_handler,
        PUT_REQ_QUEUE,
        SOURCE_ENTITY_QUEUE,
        TM_QUEUE,
    )

    # Enable all indications.
    dest_fault_handler = CfdpFaultHandler(BASE_STR_DEST)
    dest_user = CfdpUser(BASE_STR_DEST, PUT_REQ_QUEUE)
    dest_handler = DestHandler(
        cfg=LocalEntityCfg(LOCAL_ENTITY_ID, INDICATION_CFG, dest_fault_handler),
        user=dest_user,
        remote_cfg_table=remote_cfg_table,
        check_timer_provider=check_timer_provider,
    )
    dest_entity_task = DestEntityHandler(
        BASE_STR_DEST,
        logging_level,
        dest_handler,
        DEST_ENTITY_QUEUE,
        TM_QUEUE,
    )

    udp_server = UdpServer(
        0.1,
        ("127.0.0.1", LOCAL_PORT),
        ("127.0.0.1", REMOTE_PORT),
        TM_QUEUE,
        SOURCE_ENTITY_QUEUE,
        DEST_ENTITY_QUEUE,
    )

    source_entity_task.start()
    dest_entity_task.start()
    udp_server.start()

    source_entity_task.join()
    dest_entity_task.join()
    udp_server.join()


if __name__ == "__main__":
    main()
