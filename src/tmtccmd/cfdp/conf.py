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
    WITH_CRC_CONFIG_ID = 2


__CFDP_DICT = {
    CfdpConfKeys.LEN_ENTITY_ID: LenInBytes.FOUR_BYTES,
    CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM: LenInBytes.TWO_BYTES,
    CfdpConfKeys.CRC_CONFIG_ID: True
}


def set_default_length_entity_id(new_len: int):
    __CFDP_DICT[CfdpConfKeys.LEN_ENTITY_ID] = new_len


def get_default_length_entity_id() -> int:
    return __CFDP_DICT[CfdpConfKeys.LEN_ENTITY_ID]


def set_default_length_transaction_seq_num(new_len: int):
    __CFDP_DICT[CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM] = new_len


def get_default_length_transaction_seq_num() -> int:
    return __CFDP_DICT[CfdpConfKeys.LEN_TRANSACTION_SEQ_NUM]


def set_default_pdu_crc_mode(with_crc: bool):
    __CFDP_DICT[CfdpConfKeys.WITH_CRC_CONFIG_ID] = with_crc


def get_default_pdu_crc_mode() -> bool:
    return __CFDP_DICT[CfdpConfKeys.WITH_CRC_CONFIG_ID]
