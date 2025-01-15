from spacepackets.seqcount import (  # noqa: F401
    ProvidesSeqCount,
    FileSeqCountProvider,
    PusFileSeqCountProvider,
    SeqCountProvider,
)

import warnings

warnings.warn(
    "the countdown module is deprecated and was moved to spacepackets.countdown",
    DeprecationWarning,
    stacklevel=2,
)
