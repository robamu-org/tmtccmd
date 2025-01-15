import warnings

warnings.warn(
    "the com_if module is deprecated since v4.0.0rc3. Use the com module instead",
    DeprecationWarning,
    stacklevel=2,
)

from .com import *  # noqa
