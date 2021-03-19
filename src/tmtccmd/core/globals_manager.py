

class GlobalsManager:
    """
    Global object manager singleton. Only one global instance will be created.
    The instance can be retrieved with the get_manager class method and will be created on
    the first function call
    """
    MANAGER_INSTANCE = None

    @classmethod
    def get_manager(cls):
        """
        Retrieve a handle to the global object ID manager.
        """
        if cls.MANAGER_INSTANCE is None:
            cls.MANAGER_INSTANCE = GlobalsManager()
        return cls.MANAGER_INSTANCE

    def __init__(self):
        from threading import Lock
        self.globals_dict = dict()
        self.lock = Lock()

    # noinspection PyUnresolvedReferences
    def get_global(self, global_param_key: int):
        global_param = self.globals_dict.get(global_param_key)
        if global_param is None:
            try:
                from tmtccmd.utility.tmtcc_logger import get_logger
                logger = get_logger()
                logger.error(f"The key {global_param_key} for this  global does not exist in the dictionary!")

            except ImportError:
                print("Could not import LOGGER!")
            return None
        else:
            return global_param

    def add_global(self, global_param_id: int, parameter: any):
        self.globals_dict.update({global_param_id: parameter})

    def lock_global_pool(self, timeout_seconds: float = 1) -> bool:
        return self.lock.acquire(True, timeout_seconds)

    def unlock_global_pool(self):
        self.lock.release()


def get_global(global_param_id: int):
    return GlobalsManager.get_manager().get_global(global_param_id)


def update_global(global_param_id: int, parameter: any):
    return GlobalsManager.get_manager().add_global(global_param_id, parameter)


def lock_global_pool(timeout_seconds: float = -1) -> bool:
    """
    Lock the global objects. This is important if the values are changed. Don't forget to unlock the pool
    after finishing work with the globals!
    @param: timeout_seconds Attempt to lock for this many second. Default value -1 blocks permanently until lock is
    released.
    @return: Returns whether lock was locked or not.
    """
    return GlobalsManager.get_manager().lock_global_pool(timeout_seconds)


def unlock_global_pool():
    """
    Releases the lock so other objects can use the global pool as well.
    """
    GlobalsManager.get_manager().unlock_global_pool()

