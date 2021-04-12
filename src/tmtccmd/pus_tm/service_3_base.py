from tmtccmd.ecss.tm import PusTelemetry


class Service3Base(PusTelemetry):
    """
    Base class. The TMTC core provides a Service 3 implementation which is intended to be used
    with the FSFW. However, users can define an own Service 3 implementation.

    The TMTC printer utility uses the fields defined in this base class to perform prinouts so
    if a custom class is defined, the user should implement this class and fill the fields
    in the TM handling hook if printout of the HK field and validity checking is desired.
    TODO: A HasHkDataIF would propably be even better.
    """
    def __init__(self, raw_telemetry: bytearray):
        super().__init__(raw_telemetry)
        self.object_id = bytearray()
        self.set_id = 0
        self.hk_header = []
        self.hk_content = []
        self.number_of_parameters = 0
        self.validity_buffer = bytearray()
