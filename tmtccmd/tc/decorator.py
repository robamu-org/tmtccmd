import functools

from tmtccmd.tc.procedure import DefaultProcedureInfo
from tmtccmd.tc.queue import DefaultPusQueueHelper

SERVICE_HANDLER_DICT = dict()


def service_provider(service: str):
    """Decorator. TODO: Documentation"""
    global SERVICE_HANDLER_DICT

    def actual_service_decorator(handler):
        global SERVICE_HANDLER_DICT

        @functools.wraps(handler)
        def service_handler_wrapper(
            info: DefaultProcedureInfo,
            queue_helper: DefaultPusQueueHelper,
            op_code: str,
        ):
            return handler(info, queue_helper, op_code)

        SERVICE_HANDLER_DICT.update({service: service_handler_wrapper})
        return service_handler_wrapper

    return actual_service_decorator


def route_to_registered_service_handlers(
    info: DefaultProcedureInfo, queue_helper: DefaultPusQueueHelper, op_code: str
) -> bool:
    if info.service in SERVICE_HANDLER_DICT:
        SERVICE_HANDLER_DICT[info.service](info, queue_helper, op_code)
        return True
    return False
