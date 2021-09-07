import enum


class Srv5Severity(enum.IntEnum):
    INFO = 1
    LOW_SEVERITY = 2
    MEDIUM_SEVERITY = 3
    HIGH_SEVERITY = 4


class Srv5Subservices(enum.IntEnum):
    INFO_EVENT = Srv5Severity.INFO,
    LOW_SEVERITY_EVENT = Srv5Severity.LOW_SEVERITY,
    MEDIUM_SEVERITY_EVENT = Srv5Severity.MEDIUM_SEVERITY,
    HIGH_SEVERITY_EVENT = Srv5Severity.HIGH_SEVERITY,
    ENABLE_EVENT_REPORTING = 5,
    DISABLE_EVENT_REPORTING = 6
