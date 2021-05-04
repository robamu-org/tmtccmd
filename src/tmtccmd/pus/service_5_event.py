import enum


class Severity(enum.IntEnum):
    INFO = 1
    LOW_SEVERITY = 2
    MEDIUM_SEVERITY = 3
    HIGH_SEVERITY = 4


class Srv5Subservices(enum.IntEnum):
    INFO_EVENT = Severity.INFO,
    LOW_SEVERITY_EVENT = Severity.LOW_SEVERITY,
    MEDIUM_SEVERITY_EVENT = Severity.MEDIUM_SEVERITY,
    HIGH_SEVERITY_EVENT = Severity.HIGH_SEVERITY,
    ENABLE_EVENT_REPORTING = 5,
    DISABLE_EVENT_REPORTING = 6
