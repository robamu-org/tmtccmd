from typing import Union, List, Optional, Dict, Tuple

ServiceNameT = str
ServiceInfoT = str
OpCodeNameT = Union[str, List[str]]
OpCodeInfoT = str


class OpCodeOptionBase:
    def __init__(self):
        pass


OpCodeDict = Dict[str, Tuple[OpCodeInfoT, OpCodeOptionBase]]


class OpCodeEntry:
    def __init__(self):
        self._op_code_dict_num_keys: OpCodeDict = dict()
        self._op_code_dict_str_keys: OpCodeDict = dict()

    def add(
        self,
        keys: OpCodeNameT,
        info: str,
        options: OpCodeOptionBase = OpCodeOptionBase(),
    ):
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            if key.isdigit():
                self._op_code_dict_num_keys.update({key: (info, options)})
            else:
                self._op_code_dict_str_keys.update({key: (info, options)})

    def sort_num_key_dict(self):
        self._op_code_dict_num_keys = {
            int(k): v for k, v in self._op_code_dict_num_keys.items()
        }

    def sort_text_key_dict(self):
        self._op_code_dict_str_keys = {
            k: v for k, v in sorted(self._op_code_dict_str_keys.items())
        }

    def info(self, op_code: str) -> Optional[str]:
        if op_code.isdigit():
            entry_tuple = self._op_code_dict_num_keys.get(op_code)
            if entry_tuple is not None:
                return entry_tuple[0]

        entry_tuple = self._op_code_dict_str_keys.get(op_code)
        if entry_tuple is not None:
            return entry_tuple[0]
        return None

    def __str__(self):
        return (
            f"Op codes with numeric keys: {self._op_code_dict_num_keys!r}), "
            f"op codes with text keys: {self._op_code_dict_str_keys!r}"
        )

    @property
    def op_code_dict_num_keys(self):
        return self._op_code_dict_num_keys

    @property
    def op_code_dict_str_keys(self):
        return self._op_code_dict_str_keys


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
