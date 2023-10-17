from datetime import timedelta
from spacepackets.util import UnsignedByteField
from tmtccmd.cfdp.mib import CheckTimerProvider, EntityType
from tmtccmd.util.countdown import Countdown


class TestCheckTimerProvider(CheckTimerProvider):
    def provide_check_timer(
        self,
        local_entity_id: UnsignedByteField,
        remote_entity_id: UnsignedByteField,
        entity_type: EntityType,
    ) -> Countdown:
        return Countdown(timedelta(milliseconds=5))
