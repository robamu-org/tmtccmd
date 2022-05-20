import enum
import struct


class Subservices(enum.IntEnum):
    """Unless specified, TCs and TMs are related to a request ID"""
    TC_ENABLE = 1
    TC_DISABLE = 2
    TC_RESET = 3
    TC_INSERT = 4
    TC_DELETE = 5
    TC_DELETE_WITH_FILTER = 6
    TC_TIMESHIFT = 7
    TC_TIMESHIFT_WITH_FILTER = 8
    TC_DETAIL_REPORT_TIME_BASED = 9
    TM_DETAIL_REPORT_TIME_BASED = 10
    TC_DETAIL_REPORT_FILTER_BASED = 11
    TM_DETAIL_REPORT_FILTER_BASED = 12
    TC_TIMESHIFT_ALL = 15


class TcSchedReqId:
    def __init__(self, apid: int, seq_cnt: int, src_id: int):
        self.apid = apid
        self.seq_cnt = seq_cnt
        self.src_id = src_id

    @property
    def id_u32(self):
        return (self.src_id << 32) | (self.apid << 16) | self.seq_cnt

    def pack(self) -> bytes:
        return struct.pack('!I', self.id_u32)

    def __str__(self):
        return f"Raw u32 value: {self.id_u32:#08x} | APID {self.apid:#04x} | " \
               f"Seq Cnt {self.seq_cnt} | SRC ID {self.src_id:#04x}"

    def __repr__(self):
        return f"TcSchedReqId(apid={self.apid:#04x},seq_cnt={self.seq_cnt}," \
               f"src_id={self.src_id:#04x})"

