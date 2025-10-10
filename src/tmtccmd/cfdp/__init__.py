"""Please note that this module does not contain configuration helpers, for example
to convert CLI or GUI parameters into the internalized CFDP classes. You can find all those
helpers inside the :py:mod:`tmtccmd.config.cfdp` module."""

from spacepackets.cfdp import TransactionId

from .request import CfdpRequestWrapper
