import argparse
from typing import Union, Tuple

from tmtccmd.config.definitions import ServiceOpCodeDictT
from tmtccmd.config.cfg_hook import TmTcCfgHookBase, ObjectIdDictT
from tmtccmd.logging import get_console_logger
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.tc.definitions import QueueHelper
from tmtccmd.com_if.com_interface_base import CommunicationInterface

from .definitions import APID

LOGGER = get_console_logger()


class ExampleHookClass(TmTcCfgHookBase):
    def __init__(self, json_cfg_path: str):
        super().__init__(json_cfg_path=json_cfg_path)

    def assign_communication_interface(
        self, com_if_key: str
    ) -> Union[CommunicationInterface, None]:
        from tmtccmd.config.com_if import create_communication_interface_default

        LOGGER.info("Communication interface assignment function was called")
        return create_communication_interface_default(
            com_if_key=com_if_key,
            json_cfg_path=self.json_cfg_path,
        )

    def perform_mode_operation(self, tmtc_backend: CcsdsTmtcBackend, mode: int):
        LOGGER.info("Mode operation hook was called")
        pass

    def pack_service_queue(
        self, service: Union[str, int], op_code: str, tc_queue: QueueHelper
    ):
        from tmtccmd.tc.packer import default_service_queue_preparation

        LOGGER.info("Service queue packer hook was called")
        default_service_queue_preparation(
            service=service, op_code=op_code, service_queue=tc_queue
        )

    def get_object_ids(self) -> ObjectIdDictT:
        from tmtccmd.config.objects import get_core_object_ids

        return get_core_object_ids()

    def get_tmtc_definitions(self) -> ServiceOpCodeDictT:
        from tmtccmd.config.globals import get_default_tmtc_defs

        return get_default_tmtc_defs()

    @staticmethod
    def handle_service_8_telemetry(
        object_id: int, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        pass
