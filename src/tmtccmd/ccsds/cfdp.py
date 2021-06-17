from tmtccmd.ccsds.handler import CcsdsTmHandler

class CfdpSpTmHandler(CcsdsTmHandler):
    """Handler for CFDP telemetry packets using the Space packet protocol"""
    def __init__(self, apid: int):
        super().__init__(apid=apid)

    def handle_ccsds_packet(self, packet: bytearray) -> any:
        pass
