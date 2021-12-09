import abc
import os
import shutil
import datetime
import platform

from tmtccmd.utility.logger import get_console_logger
from spacepackets.cfdp.tlv import FilestoreResponseStatusCode

LOGGER = get_console_logger()

FilestoreResult = FilestoreResponseStatusCode


class VirtualFilestore:
    @abc.abstractmethod
    def copy_procecdure_handler(
        self, file_path: str, offset: int, data: bytes
    ) -> FilestoreResponseStatusCode:
        """This is not used as part of a filestore request, it is used to build up the received
        file"""
        LOGGER.warning("Appending to file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def create_file(self, file_path: str) -> FilestoreResponseStatusCode:
        LOGGER.warning("Creating file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def delete_file(self, file_path: str) -> FilestoreResponseStatusCode:
        LOGGER.warning("Deleting file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def rename_file(
        self, _old_file_path: str, _new_file_path: str
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Renaming file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def append_file(
        self, source_file: str, appended_on_source: str
    ) -> FilestoreResponseStatusCode:
        """The source file name will be the name of the resulting file"""
        LOGGER.warning("Appending to file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def replace_file(
        self, _replaced_file: str, _source_file: str
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Replacing file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def create_directory(self, _dir_name: str) -> FilestoreResponseStatusCode:
        LOGGER.warning("Creating directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def remove_directory(
        self, _dir_name: str, recursive: bool
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Removing directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def list_directory(
        self, _dir_name: str, _file_name: str, _recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Listing directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED


class HostFilestore(VirtualFilestore):
    def __init__(self):
        pass

    @abc.abstractmethod
    def copy_procecdure_handler(
        self, file_path: str, offset: int, data: bytes
    ) -> FilestoreResponseStatusCode:
        """This is not used as part of a filestore request, it is used to build up the received
        file"""
        if os.path.exists(file_path) and offset == 0:
            LOGGER.warning(
                "Offset is 0 and file already exists. Rejecting copy procedure"
            )
            return FilestoreResponseStatusCode.COPY_PROC_OFFSET_ZERO_FILE_EXISTS
        elif not os.path.exists(file_path):
            file = open(file_path, "wb")
            file_size = os.path.getsize(file_path)
        else:
            file = open(file_path, "r+b")
            file_size = os.path.getsize(file_path)
        if offset > file_size:
            return FilestoreResponseStatusCode.NOT_PERFORMED
        file.seek(offset=offset)
        file.write(data)
        file.close()
        return FilestoreResponseStatusCode.SUCCESS

    def create_file(self, file_path: str) -> FilestoreResponseStatusCode:
        """Returns CREATE_NOT_ALLOWED if the file already exists"""
        if os.path.exists(file_path):
            LOGGER.warning("File already exists")
            return FilestoreResponseStatusCode.CREATE_NOT_ALLOWED
        try:
            file = open(file_path, "x")
            file.close()
            return FilestoreResponseStatusCode.CREATE_SUCCESS
        except OSError:
            LOGGER.exception(f"Creating file {file_path} failed")
            return FilestoreResponseStatusCode.CREATE_NOT_ALLOWED

    def delete_file(self, file_path: str) -> FilestoreResponseStatusCode:
        if not os.path.exists(file_path):
            return FilestoreResponseStatusCode.DELETE_FILE_DOES_NOT_EXIST
        try:
            os.remove(file_path)
            return FilestoreResponseStatusCode.DELETE_SUCCESS
        except IsADirectoryError:
            LOGGER.exception(f"{file_path} is a directory")
            return FilestoreResponseStatusCode.DELETE_NOT_ALLOWED

    def rename_file(
        self, old_file_path: str, new_file_path: str
    ) -> FilestoreResponseStatusCode:
        if os.path.isdir(old_file_path) or os.path.isdir(new_file_path):
            LOGGER.exception(f"{old_file_path} or {new_file_path} is a directory")
            return FilestoreResponseStatusCode.RENAME_NOT_PERFORMED
        if not os.path.exists(old_file_path):
            return FilestoreResponseStatusCode.RENAME_OLD_FILE_DOES_NOT_EXIST
        if os.path.exists(new_file_path):
            return FilestoreResponseStatusCode.RENAME_NEW_FILE_DOES_EXIST
        os.rename(old_file_path, new_file_path)
        return FilestoreResponseStatusCode.RENAME_SUCCESS

    def append_file(
        self, source_file: str, appended_on_source: str
    ) -> FilestoreResponseStatusCode:
        if not os.path.exists(source_file):
            return FilestoreResponseStatusCode.APPEND_FILE_NAME_ONE_NOT_EXISTS
        if not os.path.exists(appended_on_source):
            return FilestoreResponseStatusCode.APPEND_FILE_NAME_TWO_NOT_EXISTS
        try:
            file_one = open(source_file, "ab")
            file_two = open(appended_on_source, "rb")
            file_one.write(file_two.read())
            file_one.close()
            file_two.close()
            return FilestoreResponseStatusCode.APPEND_SUCCESS
        except IOError:
            LOGGER.exception(f"Appending {appended_on_source} on {source_file} failed")
            return FilestoreResponseStatusCode.APPEND_NOT_PERFORMED

    def replace_file(
        self, replaced_file: str, source_file: str
    ) -> FilestoreResponseStatusCode:
        if os.path.isdir(replaced_file) or os.path.isdir(source_file):
            LOGGER.warning(f"{replaced_file} is a directory")
            return FilestoreResponseStatusCode.REPLACE_NOT_ALLOWED
        if not os.path.exists(replaced_file):
            return FilestoreResponseStatusCode.REPLACE_FILE_NAME_ONE_TO_BE_REPLACED_DOES_NOT_EXIST
        if not os.path.exists(source_file):
            return FilestoreResponseStatusCode.REPLACE_FILE_NAME_TWO_REPLACE_SOURCE_NOT_EXIST
        os.replace(replaced_file, source_file)

    def remove_directory(
        self, dir_name: str, recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        if not os.path.exists(dir_name):
            LOGGER.warning(f"{dir_name} does not exist")
            return FilestoreResponseStatusCode.REMOVE_DIR_DOES_NOT_EXIST
        elif not os.path.isdir(dir_name):
            LOGGER.warning(f"{dir_name} is not a directory")
            return FilestoreResponseStatusCode.REMOVE_DIR_NOT_ALLOWED
        if recursive:
            shutil.rmtree(dir_name)
        else:
            try:
                os.rmdir(dir_name)
                return FilestoreResponseStatusCode.REMOVE_DIR_SUCCESS
            except OSError:
                LOGGER.exception(f"Removing directory {dir_name} failed")
                return FilestoreResponseStatusCode.RENAME_NOT_PERFORMED

    def create_directory(self, dir_name: str) -> FilestoreResponseStatusCode:
        if os.path.exists(dir_name):
            # It does not really matter if the existing structure is a file or a directory
            return FilestoreResponseStatusCode.CREATE_DIR_CAN_NOT_BE_CREATED
        os.mkdir(dir_name)
        return FilestoreResponseStatusCode.CREATE_DIR_SUCCESS

    def list_directory(
        self, dir_name: str, file_name: str, recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        """List a directory

        :param dir_name: Name of directory to list
        :param file_name: The list will be written into this target file
        :param recursive:
        :return:
        """
        # Create a unique name by using the current time
        if os.path.exists(file_name):
            # This really should not happen
            LOGGER.warning("Duplicate file name for listing directory")
            return FilestoreResponseStatusCode.NOT_PERFORMED
        file = open(file_name, "w")
        if platform.system() == "Linux" or platform.system() == "Darwin":
            cmd = "ls -al"
        elif platform.system() == "Windows":
            cmd = "dir"
        else:
            LOGGER.warning(f"Unknown OS {platform.system()}, do not know how to list directory")
            return FilestoreResponseStatusCode.NOT_PERFORMED
        file.write(f"Contents of directory {dir_name} generated with '{cmd}':\n")
        file.close()
        curr_path = os.getcwd()
        os.chdir(dir_name)
        os.system(f'{cmd} >> {file_name}')
        os.chdir(curr_path)
        return FilestoreResponseStatusCode.SUCCESS
