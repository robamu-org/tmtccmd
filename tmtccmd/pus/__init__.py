from enum import IntEnum
from spacepackets.ecss.defs import PusServices
from .seqcnt import FileSeqCountProvider, ProvidesSeqCount


class CustomPusServices(IntEnum):
    SERVICE_200_MODE = 200
