from typing import Union, List, Optional, Dict, Tuple, Callable, Any

ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
OpCodeInfoT = str


class OpCodeOptionBase:
    def __init__(self):
        pass


OpCodeDictT = Dict[str, Tuple[OpCodeInfoT, OpCodeOptionBase]]


class OpCodeEntry:
    def __init__(self, init_dict: Optional[OpCodeDictT] = None):
        if init_dict is not None:
            self._op_code_dict = init_dict
        else:
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

    def __repr__(self):
        return f"{self.__class__.__name__}(init_dict={self._op_code_dict!r})"

    @property
    def op_code_dict(self):
        return self._op_code_dict


# It is possible to specify a service without any op codes
ServiceDictValueT = Optional[Tuple[ServiceInfoT, OpCodeEntry]]
ServiceOpCodeDictT = Dict[ServiceNameT, ServiceDictValueT]


class TmtcDefinitionWrapper:
    def __init__(self, init_defs: Optional[ServiceOpCodeDictT] = None):
        if init_defs is None:
            self.defs: ServiceOpCodeDictT = dict()
        else:
            self.defs = init_defs

    def __repr__(self):
        return f"{self.__class__.__name__}(init_defs={self.defs!r}"

    def add_service(
        self,
        name: str,
        info: str,
        op_code_entry: OpCodeEntry,
    ):
        self.defs.update({name: (info, op_code_entry)})

    def op_code_entry(self, service_name: str) -> Optional[OpCodeEntry]:
        srv_entry = self.defs.get(service_name)
        if srv_entry is not None:
            return srv_entry[1]
        return None

    def sort(self):
        self.defs = {key: self.defs[key] for key in sorted(self.defs.keys())}


REGISTER_CBS = set()


def tmtc_definitions_provider(adder_func):
    """Function decorator which registers the decorated function to be a TMTC definition provider.
    The :py:func:`execute_tmtc_def_functions` function can be used to call all functions.

    It is expected that the decorated function takes the py:class:`TmTcDefWrapper` as the first
    argument. The user can pass any additional arguments as positional and keyword
    arguments.
    """
    global REGISTER_CBS

    def call_explicitely(defs: TmtcDefinitionWrapper, *args, **kwargs):
        if REGISTER_CBS and adder_func in REGISTER_CBS:
            REGISTER_CBS.remove(adder_func)
        print(f"{adder_func.__name__} called explicitely, not necessary")
        return adder_func(defs, args, kwargs)

    REGISTER_CBS.add(adder_func)
    return call_explicitely


def call_all_definitions_providers(defs: TmtcDefinitionWrapper, *args, **kwargs):
    global REGISTER_CBS
    if REGISTER_CBS:
        for register_cb in REGISTER_CBS.copy():
            if args and kwargs:
                register_cb(defs, args, kwargs)
            if args and not kwargs:
                register_cb(defs, args)
            elif not args and not kwargs:
                register_cb(defs)
            REGISTER_CBS.remove(register_cb)
