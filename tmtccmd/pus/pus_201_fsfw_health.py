import enum


class Subservice(enum.IntEnum):
    TC_SET_HEALTH = 1
    TM_HEALTH_SET = 2
    TC_ANNOUNCE_HEALTH = 3
    TC_ANNOUNCE_HEALTH_ALL = 4
