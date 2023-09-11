from pathlib import Path
from typing import Optional

from spacepackets.cfdp import CfdpLv
from spacepackets.cfdp.tlv import ProxyPutRequestParams, ProxyPutRequest
from spacepackets.util import UnsignedByteField
from tmtccmd.cfdp.request import PutRequest
from tmtccmd.config.defs import CfdpParams


def cfdp_req_to_put_req_regular(
    params: CfdpParams, dest_id: UnsignedByteField
) -> Optional[PutRequest]:
    if not params.proxy_op:
        return PutRequest(
            destination_id=dest_id,
            source_file=Path(params.source_file),
            dest_file=Path(params.dest_file),
            closure_requested=params.closure_requested,
            trans_mode=params.transmission_mode,
        )
    return None


def cfdp_req_to_put_req_get_req(
    params: CfdpParams, local_id: UnsignedByteField, remote_id: UnsignedByteField
) -> Optional[PutRequest]:
    """This function converts the internalized CFDP parameters to the get request variant of the
    :py:class:`tmtccmd.cfdp.request.PutRequest` class. Please note that the local ID refers to
    the receiver of the target of the file copy operation for a get request while the remote ID
    refers to the sender component for the file copy operation."""
    return cfdp_req_to_put_req_proxy_put_req(
        params, dest_id_put_request=remote_id, dest_id_proxy_put_req=local_id
    )


def cfdp_req_to_put_req_proxy_put_req(
    params: CfdpParams,
    dest_id_put_request: UnsignedByteField,
    dest_id_proxy_put_req: UnsignedByteField,
) -> Optional[PutRequest]:
    """Generic function to convert the internalized CFDP parameters to a proxy put request.

    :param params: CFDP parameters
    :param dest_id_put_request: Recipient of the put request.
    :param dest_id_proxy_put_req: Recipient of the proxy put operation. For a get request, this
        should the the ID of the sender.
    """
    if not params.proxy_op:
        return None
    proxy_put_params = ProxyPutRequestParams(
        dest_entity_id=dest_id_proxy_put_req,
        source_file_name=CfdpLv.from_str(params.source_file),
        dest_file_name=CfdpLv.from_str(params.dest_file),
    )
    proxy_put_req = ProxyPutRequest(proxy_put_params)
    return PutRequest(
        destination_id=dest_id_put_request,
        msgs_to_user=[proxy_put_req.to_generic_msg_to_user_tlv()],
        closure_requested=None,
        dest_file=None,
        source_file=None,
        trans_mode=None,
    )


def generic_cfdp_params_to_put_request(
    params: CfdpParams,
    local_id: UnsignedByteField,  # noqa
    remote_id: UnsignedByteField,
    dest_id_proxy_put_req: UnsignedByteField,
) -> Optional[PutRequest]:
    """Please note that this function currently only has the following functionality. It
    might be extended in the future to have more functionality, or be converted to a factory
    class.

    1. Create a regular put request for a file copy operation.
    2. Create a proxy put request."""
    if params.proxy_op:
        return cfdp_req_to_put_req_proxy_put_req(
            params,
            remote_id,
            dest_id_proxy_put_req,
        )
    else:
        return cfdp_req_to_put_req_regular(params, remote_id)
