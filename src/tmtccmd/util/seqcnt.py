import warnings

from spacepackets.seqcount import (  # noqa: F401
    FileSeqCountProvider,
    ProvidesSeqCount,
    PusFileSeqCountProvider,
    SeqCountProvider,
)

warnings.warn(
    "the countdown module is deprecated and was moved to spacepackets.countdown",
    DeprecationWarning,
    stacklevel=2,
)
