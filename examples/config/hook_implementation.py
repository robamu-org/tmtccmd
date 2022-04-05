import argparse
from typing import Union, Tuple

from tmtccmd.config.definitions import ServiceOpCodeDictT
from tmtccmd.config.hook import TmTcHookBase, ObjectIdDictT
from tmtccmd.logging import get_console_logger
from tmtccmd.core.backend import TmTcHandler
from tmtccmd.tc.definitions import TcQueueT
from tmtccmd.com_if.com_interface_base import CommunicationInterface

from config.definitions import APID

LOGGER = get_console_logger()


class ExampleHookClass(TmTcHookBase):
    def add_globals_pre_args_parsing(self, gui: bool = False):
        from tmtccmd.config.globals import set_default_globals_pre_args_parsing

        set_default_globals_pre_args_parsing(gui=gui, tc_apid=APID, tm_apid=APID)

    def add_globals_post_args_parsing(self, args: argparse.Namespace):
        from tmtccmd.config.globals import set_default_globals_post_args_parsing

        set_default_globals_post_args_parsing(
            args=args, json_cfg_path=self.get_json_config_file_path()
        )

    def assign_communication_interface(
        self, com_if_key: str
    ) -> Union[CommunicationInterface, None]:
        from tmtccmd.config.com_if import create_communication_interface_default

        LOGGER.info("Communication interface assignment function was called")
        return create_communication_interface_default(
            com_if_key=com_if_key,
            json_cfg_path=self.get_json_config_file_path(),
        )

    def perform_mode_operation(self, tmtc_backend: TmTcHandler, mode: int):
        LOGGER.info("Mode operation hook was called")
        pass

    def pack_service_queue(
        self, service: Union[str, int], op_code: str, service_queue: TcQueueT
    ):
        from tmtccmd.tc.packer import default_service_queue_preparation

        LOGGER.info("Service queue packer hook was called")
        default_service_queue_preparation(
            service=service, op_code=op_code, service_queue=service_queue
        )

    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        return get_core_object_ids()

    def get_service_op_code_dictionary(self) -> ServiceOpCodeDictT:
        from tmtccmd.config.globals import get_default_service_op_code_dict

        return get_default_service_op_code_dict()

    @staticmethod
    def handle_service_8_telemetry(
        object_id: int, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        pass
