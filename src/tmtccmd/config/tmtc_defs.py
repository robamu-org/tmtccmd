from typing import Union, List, Optional, Dict, Tuple

ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
OpCodeInfoT = str


class OpCodeOptionBase:
    def __init__(self):
        pass


OpCodeDictT = Dict[str, Tuple[OpCodeInfoT, OpCodeOptionBase]]


class OpCodeEntry:
    def __init__(self):
        self._op_code_dict: OpCodeDictT = dict()

    def add(
        self,
        keys: OpCodeNameT,
        info: str,
        options: OpCodeOptionBase = OpCodeOptionBase(),
    ):
        if isinstance(keys, str):
            keys = [keys]
        self._op_code_dict.update(OpCodeDictT.fromkeys(keys, (info, options)))

    def sort(self):
        self._op_code_dict = {
            key: self._op_code_dict[key] for key in sorted(self._op_code_dict.keys())
        }

    def info(self, op_code: str) -> Optional[str]:
        entry_tuple = self._op_code_dict.get(op_code)
        if entry_tuple is not None:
            return entry_tuple[0]

    @property
    def op_code_dict(self):
        return self._op_code_dict


# It is possible to specify a service without any op codes
ServiceDictValueT = Optional[Tuple[ServiceInfoT, OpCodeEntry]]
ServiceOpCodeDictT = Dict[ServiceNameT, ServiceDictValueT]


class TmTcDefWrapper:
    def __init__(self):
        self.defs: ServiceOpCodeDictT = dict()
        pass

    def add_service(
        self,
        service_name: str,
        info: str,
        op_code_entry: OpCodeEntry,
    ):
        self.defs.update({service_name: (info, op_code_entry)})

    def op_code_entry(self, service_name: str) -> Optional[OpCodeEntry]:
        srv_entry = self.defs.get(service_name)
        if srv_entry is not None:
            return srv_entry[1]
        return None

    def sort(self):
        self.defs = {key: self.defs[key] for key in sorted(self.defs.keys())}
