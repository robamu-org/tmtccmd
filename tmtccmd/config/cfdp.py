from pathlib import Path
from typing import Optional

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.defs import Direction
from spacepackets.cfdp.tlv import ProxyPutRequestParams, ProxyPutRequest
from spacepackets.util import UnsignedByteField
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.config.defs import CfdpParams


class CfdpCfg:
    direction = Direction.TOWARDS_SENDER
    source_file_name = ""
    dest_file_name = ""


def cfdp_req_to_put_req_regular(
    params: CfdpParams, dest_id: UnsignedByteField
) -> Optional[PutRequest]:
    if not params.proxy_op:
        return PutRequest(
            destination_id=dest_id,
            source_file=Path(params.source_file),
            dest_file=params.dest_file,
            closure_requested=params.closure_requested,
            trans_mode=params.transmission_mode,
        )
    return None


def cfdp_req_to_put_req_proxy_get_req(
    params: CfdpParams, local_id: UnsignedByteField, remote_id: UnsignedByteField
) -> Optional[PutRequest]:
    """This function converts the internalized CFDP parameters to the get request variant of the
    :py:class:`tmtccmd.config.defs.PutRequest` class. Please note that the local ID refers to
    the receiver of the target of the file copy operation for a get request while the remote ID
    refers to the sender component for the file copy operation."""
    if not params.proxy_op:
        return None
    proxy_put_params = ProxyPutRequestParams(
        dest_entity_id=local_id,
        source_file_name=CfdpLv.from_str(params.source_file),
        dest_file_name=CfdpLv.from_str(params.dest_file),
    )
    proxy_put_req = ProxyPutRequest(proxy_put_params)
    return PutRequest(
        destination_id=remote_id,
        msgs_to_user=[proxy_put_req.to_generic_msg_to_user_tlv()],
        closure_requested=None,
        dest_file=None,
        source_file=None,
        trans_mode=None,
    )
