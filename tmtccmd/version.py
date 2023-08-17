from importlib import metadata


def get_version() -> str:
    return metadata.version("tmtccmd")
