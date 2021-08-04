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


class CfdpConfKeys(enum.IntEnum):
    LEN_ENTITY_ID = 0
    LEN_TRANSACTION_SEQ_NUM = 1


__CFDP_DICT = {
    CfdpConfKeys.LEN_ENTITY_ID: LenInBytes.FOUR_BYTES,
    CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM: LenInBytes.TWO_BYTES
}


def set_default_length_entity_id(new_len: int):
    __CFDP_DICT[CfdpConfKeys.LEN_ENTITY_ID] = new_len


def get_default_length_entity_id() -> int:
    return __CFDP_DICT[CfdpConfKeys.LEN_ENTITY_ID]


def set_default_length_transaction_seq_num(new_len: int):
    __CFDP_DICT[CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM] = new_len


def get_default_length_transaction_seq_num() -> int:
    return __CFDP_DICT[CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM]
