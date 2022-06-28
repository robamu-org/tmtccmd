import abc
import os
import shutil
import platform
from pathlib import Path

from tmtccmd.logging import get_console_logger
from spacepackets.cfdp.tlv import FilestoreResponseStatusCode

LOGGER = get_console_logger()

FilestoreResult = FilestoreResponseStatusCode


class VirtualFilestore:
    @abc.abstractmethod
    def append_data_to_file(
        self, file: Path, offset: int, data: bytes
    ) -> FilestoreResponseStatusCode:
        """This is not used as part of a filestore request, it is used to build up the received
        file"""
        LOGGER.warning("Appending to file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def create_file(self, file: Path) -> FilestoreResponseStatusCode:
        LOGGER.warning("Creating file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def delete_file(self, file: Path) -> FilestoreResponseStatusCode:
        LOGGER.warning("Deleting file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def rename_file(
        self, _old_file: Path, _new_file: Path
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Renaming file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def replace_file(
        self, _replaced_file: Path, _source_file: Path
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Replacing file not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def create_directory(self, _dir_name: Path) -> FilestoreResponseStatusCode:
        LOGGER.warning("Creating directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def remove_directory(
        self, _dir_name: Path, recursive: bool
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Removing directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED

    @abc.abstractmethod
    def list_directory(
        self, _dir_name: Path, _file_name: Path, _recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        LOGGER.warning("Listing directory not implemented in virtual filestore")
        return FilestoreResponseStatusCode.NOT_PERFORMED


class HostFilestore(VirtualFilestore):
    def __init__(self):
        pass

    @abc.abstractmethod
    def append_data_to_file(
        self, file: Path, offset: int, data: bytes
    ) -> FilestoreResponseStatusCode:
        """Primary function used to perform the CFDP Copy Procedure. This will also create a new
        file as long as no other file with the same name exists

        :return:
         - FilestoreResponseStatusCode.APPEND_FROM_DATA_FILE_NOT_EXISTS: File does not exist yet
         - FilestoreResponseStatusCode.APPEND_FROM_DATA_INVALID_OFFSET: Invalid offset
        """
        if not file.exists():
            return FilestoreResponseStatusCode.APPEND_FROM_DATA_FILE_NOT_EXISTS
        with open(file, "r+b") as of:
            file_size = file.stat().st_size
            if offset > file_size:
                return FilestoreResponseStatusCode.APPEND_FROM_DATA_INVALID_OFFSET
            of.seek(offset)
            of.write(data)
        return FilestoreResponseStatusCode.SUCCESS

    def create_file(self, file: Path) -> FilestoreResponseStatusCode:
        """Returns CREATE_NOT_ALLOWED if the file already exists"""
        if file.exists():
            LOGGER.warning("File already exists")
            return FilestoreResponseStatusCode.CREATE_NOT_ALLOWED
        try:
            file = open(file, "x")
            file.close()
            return FilestoreResponseStatusCode.CREATE_SUCCESS
        except OSError:
            LOGGER.exception(f"Creating file {file} failed")
            return FilestoreResponseStatusCode.CREATE_NOT_ALLOWED

    def delete_file(self, file: Path) -> FilestoreResponseStatusCode:
        if not file.exists():
            return FilestoreResponseStatusCode.DELETE_FILE_DOES_NOT_EXIST
        if file.is_dir():
            return FilestoreResponseStatusCode.DELETE_NOT_ALLOWED
        os.remove(file)
        return FilestoreResponseStatusCode.DELETE_SUCCESS

    def rename_file(
        self, old_file: Path, new_file: Path
    ) -> FilestoreResponseStatusCode:
        if old_file.is_dir() or new_file.is_dir():
            LOGGER.exception(f"{old_file} or {new_file} is a directory")
            return FilestoreResponseStatusCode.RENAME_NOT_PERFORMED
        if not old_file.exists():
            return FilestoreResponseStatusCode.RENAME_OLD_FILE_DOES_NOT_EXIST
        if new_file.exists():
            return FilestoreResponseStatusCode.RENAME_NEW_FILE_DOES_EXIST
        old_file.rename(new_file)
        return FilestoreResponseStatusCode.RENAME_SUCCESS

    def replace_file(
        self, replaced_file: Path, source_file: Path
    ) -> FilestoreResponseStatusCode:
        if replaced_file.is_dir() or source_file.is_dir():
            LOGGER.warning(f"{replaced_file} is a directory")
            return FilestoreResponseStatusCode.REPLACE_NOT_ALLOWED
        if not replaced_file.exists():
            return (
                FilestoreResponseStatusCode.REPLACE_FILE_NAME_ONE_TO_BE_REPLACED_DOES_NOT_EXIST
            )
        if not source_file.exists():
            return (
                FilestoreResponseStatusCode.REPLACE_FILE_NAME_TWO_REPLACE_SOURCE_NOT_EXIST
            )
        source_file.replace(replaced_file)

    def remove_directory(
        self, dir_name: Path, recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        if not dir_name.exists():
            LOGGER.warning(f"{dir_name} does not exist")
            return FilestoreResponseStatusCode.REMOVE_DIR_DOES_NOT_EXIST
        elif not dir_name.is_dir():
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

    def create_directory(self, dir_name: Path) -> FilestoreResponseStatusCode:
        if dir_name.exists():
            # It does not really matter if the existing structure is a file or a directory
            return FilestoreResponseStatusCode.CREATE_DIR_CAN_NOT_BE_CREATED
        os.mkdir(dir_name)
        return FilestoreResponseStatusCode.CREATE_DIR_SUCCESS

    def list_directory(
        self, dir_name: Path, target_file: Path, recursive: bool = False
    ) -> FilestoreResponseStatusCode:
        """List a directory

        :param dir_name: Name of directory to list
        :param target_file: The list will be written into this target file
        :param recursive:
        :return:
        """
        if target_file.exists():
            open_flag = "a"
        else:
            open_flag = "w"
        with open(target_file, open_flag) as of:
            if platform.system() == "Linux" or platform.system() == "Darwin":
                cmd = "ls -al"
            elif platform.system() == "Windows":
                cmd = "dir"
            else:
                LOGGER.warning(
                    f"Unknown OS {platform.system()}, do not know how to list directory"
                )
                return FilestoreResponseStatusCode.NOT_PERFORMED
            of.write(f"Contents of directory {dir_name} generated with '{cmd}':\n")
            curr_path = os.getcwd()
            os.chdir(dir_name)
            os.system(f"{cmd} >> {target_file}")
            os.chdir(curr_path)
        return FilestoreResponseStatusCode.SUCCESS
