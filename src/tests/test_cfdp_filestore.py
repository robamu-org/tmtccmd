import os.path
import shutil
from pyfakefs.fake_filesystem_unittest import TestCase
from tmtccmd.cfdp.filestore import HostFilestore, FilestoreResult


TEST_FILE_NAME_0 = "/tmp/cfdp_unittest0.txt"
TEST_FILE_NAME_1 = "/tmp/cfdp_unittest1.txt"
TEST_DIR_NAME_0 = "/tmp/cfdp_test_folder0"
TEST_DIR_NAME_1 = "/tmp/cfdp_test_folder1"
TEST_LIST_DIR_NAME = "/tmp/list-dir-test.txt"


class TestCfdpHostFilestore(TestCase):
    def test_filestore(self):
        filestore = HostFilestore()
        if os.path.exists(TEST_FILE_NAME_0):
            if os.path.isdir(TEST_DIR_NAME_0):
                os.rmdir(TEST_FILE_NAME_0)
            else:
                os.remove(TEST_FILE_NAME_0)
        if os.path.exists(TEST_FILE_NAME_1):
            if os.path.isdir(TEST_DIR_NAME_1):
                os.rmdir(TEST_FILE_NAME_1)
            else:
                os.remove(TEST_FILE_NAME_1)
        if os.path.exists(TEST_DIR_NAME_0):
            shutil.rmtree(TEST_DIR_NAME_0)
        if os.path.exists(TEST_DIR_NAME_1):
            shutil.rmtree(TEST_DIR_NAME_1)
        res = filestore.create_file(TEST_FILE_NAME_0)
        self.assertTrue(res == FilestoreResult.CREATE_SUCCESS)
        self.assertTrue(os.path.exists(TEST_FILE_NAME_0))
        res = filestore.create_file(TEST_FILE_NAME_0)
        self.assertTrue(res == FilestoreResult.CREATE_NOT_ALLOWED)

        res = filestore.delete_file(TEST_FILE_NAME_0)
        self.assertTrue(res == FilestoreResult.DELETE_SUCCESS)
        self.assertFalse(os.path.exists(TEST_FILE_NAME_0))
        res = filestore.delete_file(TEST_FILE_NAME_0)
        self.assertTrue(res == FilestoreResult.DELETE_FILE_DOES_NOT_EXIST)

        filestore.create_file(TEST_FILE_NAME_0)
        res = filestore.rename_file(
            old_file_path=TEST_FILE_NAME_0, new_file_path=TEST_FILE_NAME_1
        )
        self.assertTrue(res == FilestoreResult.RENAME_SUCCESS)
        self.assertTrue(os.path.exists(TEST_FILE_NAME_1))
        self.assertFalse(os.path.exists(TEST_FILE_NAME_0))
        res = filestore.delete_file(TEST_FILE_NAME_1)
        self.assertTrue(res == FilestoreResult.DELETE_SUCCESS)

        res = filestore.create_directory(TEST_DIR_NAME_0)
        self.assertTrue(res == FilestoreResult.CREATE_DIR_SUCCESS)
        self.assertTrue(os.path.isdir(TEST_DIR_NAME_0))
        res = filestore.create_directory(TEST_DIR_NAME_0)
        self.assertTrue(res == FilestoreResult.CREATE_DIR_CAN_NOT_BE_CREATED)

        res = filestore.delete_file(TEST_DIR_NAME_0)
        self.assertTrue(res == FilestoreResult.DELETE_NOT_ALLOWED)
        res = filestore.remove_directory(TEST_DIR_NAME_0)
        self.assertTrue(res == FilestoreResult.REMOVE_DIR_SUCCESS)

    def test_list_dir(self):
        filestore = HostFilestore()
        if os.path.exists(TEST_LIST_DIR_NAME):
            os.remove(TEST_LIST_DIR_NAME)
        # Do not delete, user can check file content now
        res = filestore.list_directory(dir_name="/tmp", file_name=TEST_LIST_DIR_NAME)
        self.assertTrue(res == FilestoreResult.SUCCESS)
