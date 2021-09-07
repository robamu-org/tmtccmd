import enum


class LenInBytes(enum.IntEnum):
    ONE_BYTE = 0
    TWO_BYTES = 1
    THREE_BYTES = 2
    FOUR_BYTES = 3
    FIVE_BYTES = 4
    SIX_BYTES = 5
    SEVEN_BYTES = 6
    EIGHT_BYTES = 7
    NONE = 99


class ChecksumTypes(enum.IntEnum):
    pass
