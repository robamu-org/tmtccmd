import enum
from tmtccmd.cfdp.definitions import LenInBytes
from tmtccmd.ccsds.log import LOGGER


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


def check_packet_length(raw_packet_len: int, min_len: int, warn_on_fail: bool = True) -> bool:
    """Check whether the length of a raw packet is shorter than a specified expectedminimum length.
    By defaults, prints a warning if this is the case
    :param raw_packet_len:
    :param min_len:
    :param warn_on_fail:
    :return: Returns True if the raw packet is larger than the specified minimum length, False
    otherwise
    """
    if raw_packet_len < min_len:
        if warn_on_fail:
            LOGGER.warning(
                f'Detected packet length {raw_packet_len}, smaller than expected {min_len}'
            )
        return False
    return True
