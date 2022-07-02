import os.path
from pathlib import Path
import shutil
import tempfile

from pyfakefs.fake_filesystem_unittest import TestCase
from tmtccmd.cfdp.filestore import HostFilestore, FilestoreResult


class TestCfdpHostFilestore(TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.temp_dir = tempfile.gettempdir()
        self.test_file_name_0 = Path(f"{self.temp_dir}/cfdp_unittest0.txt")
        self.test_file_name_1 = Path(f"{self.temp_dir}/cfdp_unittest1.txt")
        self.test_dir_name_0 = Path(f"{self.temp_dir}/cfdp_test_folder0")
        self.test_dir_name_1 = Path(f"{self.temp_dir}/cfdp_test_folder1")
        self.test_list_dir_name = Path(f"{self.temp_dir}/list-dir-test.txt")

    def test_filestore(self):
        filestore = HostFilestore()

        res = filestore.create_file(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.CREATE_SUCCESS)
        self.assertTrue(self.test_file_name_0.exists())
        res = filestore.create_file(self.test_file_name_0)
        self.assertEqual(res, FilestoreResult.CREATE_NOT_ALLOWED)

        res = filestore.delete_file(self.test_file_name_0)
        self.assertEqual(res, FilestoreResult.DELETE_SUCCESS)
        self.assertFalse(os.path.exists(self.test_file_name_0))
        res = filestore.delete_file(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.DELETE_FILE_DOES_NOT_EXIST)

        filestore.create_file(self.test_file_name_0)
        res = filestore.rename_file(self.test_file_name_0, self.test_file_name_1)
        self.assertTrue(res == FilestoreResult.RENAME_SUCCESS)
        self.assertTrue(os.path.exists(self.test_file_name_1))
        self.assertFalse(os.path.exists(self.test_file_name_0))
        res = filestore.delete_file(self.test_file_name_1)
        self.assertTrue(res == FilestoreResult.DELETE_SUCCESS)

        res = filestore.create_directory(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.CREATE_DIR_SUCCESS)
        self.assertTrue(os.path.isdir(self.test_file_name_0))
        res = filestore.create_directory(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.CREATE_DIR_CAN_NOT_BE_CREATED)

        res = filestore.delete_file(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.DELETE_NOT_ALLOWED)
        res = filestore.remove_directory(self.test_file_name_0)
        self.assertTrue(res == FilestoreResult.REMOVE_DIR_SUCCESS)

    def test_list_dir(self):
        filestore = HostFilestore()
        tempdir = Path(tempfile.gettempdir())
        if os.path.exists(self.test_list_dir_name):
            os.remove(self.test_list_dir_name)
        # Do not delete, user can check file content now
        res = filestore.list_directory(
            dir_name=tempdir, target_file=self.test_list_dir_name
        )
        self.assertTrue(res == FilestoreResult.SUCCESS)

    def tearDown(self):
        pass
