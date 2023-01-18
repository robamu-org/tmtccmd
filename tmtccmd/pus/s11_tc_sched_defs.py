from __future__ import annotations
import enum
import struct

from spacepackets.ecss import PusTelecommand


class TypeOfTimeWindow(enum.IntEnum):
    SELECT_ALL = 0
    FROM_TIMETAG_TO_TIMETAG = 1
    FROM_TIMETAG = 2
    TO_TIMETAG = 3


class Subservice(enum.IntEnum):
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
        """
        :raises ValueError: Input invalid
        """
        if apid > pow(2, 11) or apid < 0:
            raise ValueError
        self.apid = apid
        if seq_cnt > pow(2, 16) or seq_cnt < 0:
            raise ValueError
        self.seq_cnt = seq_cnt
        if src_id > pow(2, 16) or src_id < 0:
            raise ValueError
        self.src_id = src_id

    @property
    def id_u64(self):
        return (self.src_id << 32) | (self.apid << 16) | self.seq_cnt

    def pack(self) -> bytes:
        return struct.pack("!Q", self.id_u64)

    def __str__(self):
        return (
            f"Raw u64: {self.id_u64:#016x} | APID {self.apid:#04x} | "
            f"Seq Cnt {self.seq_cnt} | SRC ID {self.src_id:#04x}"
        )

    def __repr__(self):
        return (
            f"TcSchedReqId(apid={self.apid:#04x},seq_cnt={self.seq_cnt},"
            f"src_id={self.src_id:#04x})"
        )

    @classmethod
    def build_from_tc(cls, tc: PusTelecommand) -> TcSchedReqId:
        return TcSchedReqId(tc.pus_tc_sec_header.source_id, tc.apid, tc.seq_count)
