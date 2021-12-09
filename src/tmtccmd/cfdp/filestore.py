import abc
import os

from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class VirtualFilestore:
    @abc.abstractmethod
    def create_file(self, file_path: str):
        LOGGER.warning("Creating file not implemented in virtual filestore")

    @abc.abstractmethod
    def delete_file(self, file_path: str):
        LOGGER.warning("Deleting file not implemented in virtual filestore")

    @abc.abstractmethod
    def rename_file(self, _old_file_path: str, _new_file_path: str):
        LOGGER.warning("Renaming file not implemented in virtual filestore")

    @abc.abstractmethod
    def append_file(self, _file_path: str, _data: bytes):
        LOGGER.warning("Appending to file not implemented in virtual filestore")

    @abc.abstractmethod
    def replace_file(self, _replaced_file: str, _new_file: str):
        LOGGER.warning("Replacing file not implemented in virtual filestore")

    @abc.abstractmethod
    def create_directory(self, _dir_name: str):
        LOGGER.warning("Creating directory not implemented in virtual filestore")

    @abc.abstractmethod
    def list_directory(self, _dir_name: str, _recursive: bool):
        LOGGER.warning("Listing directory not implemented in virtual filestore")


class HostFilestore(VirtualFilestore):
    def create_file(self, file_path: str):
        pass

    def delete_file(self, file_path: str):
        pass

    def rename_file(self, _old_file_path: str, _new_file_path: str):
        pass

    def append_file(self, _file_path: str, _data: bytes):
        pass

    def replace_file(self, _replaced_file: str, _new_file: str):
        pass

    def create_directory(self, _dir_name: str):
        pass

    def list_directory(self, _dir_name: str, _recursive: bool):
        pass
