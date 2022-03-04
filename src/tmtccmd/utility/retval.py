from typing import Dict


class RetvalInfo:
    def __init__(self):
        self.id: int = 0
        self.name: str = ""
        self.info: str = ""
        self.if_name: str = ""

    def id_as_hex(self) -> str:
        return f"{self.id:#04x}"

    @property
    def subsystem_id(self) -> int:
        return (self.id >> 8) & 0xFF

    @property
    def unique_id(self) -> int:
        return self.id & 0xFF


RetvalDictT = Dict[int, RetvalInfo]
