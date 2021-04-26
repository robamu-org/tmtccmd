import enum


class EcssPtc(enum.IntEnum):
    BOOLEAN = 1
    ENUMERATED = 2
    UNSIGNED = 3
    SIGNED = 4
    # Float or double values
    REAL = 5
    BIT_STRING = 6
    OCTET_STRING = 7
    CHARACTER_STRING = 8
    ABSOLUTE_TIME = 9
    RELATIVE_TIME = 10
    DEDUCED = 11
    PACKET = 12


class EcssPfcUnsigned(enum.IntEnum):
    FOUR_BIT = 0
    FIVE_BIT = 1
    SIX_BIT = 2
    SEVEN_BIT = 3
    ONE_BYTE = 4
    NINE_BIT = 5
    TEN_BIT = 6
    ELEVEN_BIT = 7
    TWELVE_BIT = 8
    THIRTEEN_BIT = 9
    FOURTEEN_BIT = 10
    FIFTEEN_BIT = 11
    TWO_BYTES = 12
    THREE_BYTES = 13
    FOUR_BYTES = 14
    SIX_BYTES = 15
    EIGHT_BYTES = 16
    ONE_BIT = 17
    TWO_BIT = 18
    THREE_BIT = 19


class EcssPfcSigned(enum.IntEnum):
    FOUR_BIT = 0
    FIVE_BIT = 1
    SIX_BIT = 2
    SEVEN_BIT = 3
    ONE_BYTE = 4
    NINE_BIT = 5
    TEN_BIT = 6
    ELEVEN_BIT = 7
    TWELVE_BIT = 8
    THIRTEEN_BIT = 9
    FOURTEEN_BIT = 10
    FIFTEEN_BIT = 11
    TWO_BYTES = 12
    THREE_BYTES = 13
    FOUR_BYTES = 14
    SIX_BYTES = 15
    EIGHT_BYTES = 16


class EcssPfcReal(enum.IntEnum):
    FLOAT_SIMPLE_PRECISION_IEEE = 1
    DOUBLE_PRECISION_IEEE = 2
    FLOAT_PRECISION_MIL_STD_4_OCTETS = 3
    DOUBLE_PRECISION_MIL_STD_6_OCTETS = 4
