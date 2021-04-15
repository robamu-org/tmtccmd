import enum


class Srv17Subservices(enum.IntEnum):
    PING_CMD = 1,
    PING_REPLY = 2,
    GEN_EVENT = 128
