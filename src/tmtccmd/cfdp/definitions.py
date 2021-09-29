import enum


class LenInBytes(enum.IntEnum):
    ONE_BYTE = 0
    TWO_BYTES = 2
    FOUR_BYTES = 4
    EIGHT_BYTES = 8
    GLOBAL = 90
    NONE = 99


class ChecksumTypes(enum.IntEnum):
    pass
