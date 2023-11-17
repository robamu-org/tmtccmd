import dataclasses
import functools

from tmtccmd.tmtc import TcHandlerBase
from tmtccmd.tmtc.procedure import DefaultProcedureInfo
from tmtccmd.tmtc.queue import DefaultPusQueueHelper

SERVICE_HANDLER_DICT = dict()


@dataclasses.dataclass
class ServiceProviderParams:
    handler_base: TcHandlerBase
    info: DefaultProcedureInfo
    queue_helper: DefaultPusQueueHelper
    op_code: str


def service_provider(service: str):
    """Decorator. TODO: Documentation"""
    global SERVICE_HANDLER_DICT

    def actual_service_decorator(handler):
        global SERVICE_HANDLER_DICT

        @functools.wraps(handler)
        def service_handler_wrapper(p: ServiceProviderParams):
            return handler(p)

        SERVICE_HANDLER_DICT.update({service: service_handler_wrapper})
        return service_handler_wrapper

    return actual_service_decorator


def route_to_registered_service_handlers(
    service: str, p: ServiceProviderParams
) -> bool:
    if service in SERVICE_HANDLER_DICT:
        SERVICE_HANDLER_DICT[service](p)
        return True
    return False
