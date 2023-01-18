import enum


class FsfwHealth(enum.IntEnum):
    FAULTY = 0
    HEALTHY = 1
    EXTERNAL_CTRL = 2
    NEEDS_RECOVERY = 3
    PERMANENT_FAULTY = 4


def pack_set_health_cmd_data(object_id: bytes, health: FsfwHealth) -> bytearray:
    cmd = bytearray()
    cmd += object_id
    cmd.append(health)
    return cmd
