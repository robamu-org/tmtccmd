from typing import Deque
from tmtccmd.ecss.tm import PusTelemetry

PusTmQueue = Deque[PusTelemetry]
