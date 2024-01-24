from spacepackets.countdown import Countdown, time_ms  # noqa: F401

import warnings

warnings.warn(
    "the countdown module is deprecated and was moved to spacepackets.countdown",
    DeprecationWarning,
    stacklevel=2,
)
