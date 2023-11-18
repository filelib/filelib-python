import io
import shutil
from unittest import TestCase, mock
from uuid import uuid4

from jmstorage import Cache

from filelib import FilelibConfig, UploadManager
from filelib.constants import (
    UPLOAD_CHUNK_SIZE_HEADER,
    UPLOAD_LOCATION_HEADER,
    UPLOAD_MAX_CHUNK_SIZE_HEADER,
    UPLOAD_MIN_CHUNK_SIZE_HEADER,
    UPLOAD_PENDING
)
from filelib.exceptions import FilelibAPIException, FileNameRequiredError
from tests.mocks import mock_authentication, mock_httpx_request


class UploadManagerTestCase(TestCase):
    init_upload_201_res_headers = {
        UPLOAD_MAX_CHUNK_SIZE_HEADER: str(10000),
        UPLOAD_MIN_CHUNK_SIZE_HEADER: str(1000),
        UPLOAD_CHUNK_SIZE_HEADER: str(5000),
        UPLOAD_LOCATION_HEADER: f"https://testserver.nonexisting/api/upload/{str(uuid4())}"
    }

    init_upload_400_res_json = {
        "status": False,
        "error": "Test Error",
        "error_code": "VALIDATION_ERROR_CODE",
        "data": {}
    }

    def setUp(self):
        self.test_cache_path = "./test_tmp"
        self.file_name = "test_file.txt"
        self.file = io.BytesIO(b"iamtestfile")
        self.config = FilelibConfig(storage="test_storage")
        self.cache = Cache(namespace=self.file_name, path=self.test_cache_path)
        self.auth = mock_authentication()

        self.up = self.gen_up()

    def gen_up(self, **kwargs):
        """
        Initialize UploadManager instance and return it.
        """
        vals = dict(file=self.file, config=self.config, auth=self.auth, file_name=self.file_name, cache=self.cache)

        if kwargs:
            vals.update(kwargs)
        return UploadManager(**vals)

    def test_init_parameter_requirements(self):
        """
        Test initialization of UploadManager class
        Test against missing parameters that must be provided.
            self,
            file,
            config: FilelibConfig,
            auth: Authentication,
            file_name=None,
            cache=None,
            multithreading=False,
            workers: int = 4,
            content_type=None,
            ignore_cache=False,
            abort_on_fail=False,
            clear_cache=False
        """

        # Test missing parameter: file
        with self.assertRaises(TypeError):
            UploadManager()

        # Test missing parameter: config
        with self.assertRaises(TypeError):
            UploadManager(file=self.file)

        # Test missing parameter: auth
        with self.assertRaises(TypeError):
            UploadManager(file=self.file, config=self.config)

        # Test missing parameter: file_name when file object does not have `name` prop
        with self.assertRaises(FileNameRequiredError):
            UploadManager(file=self.file, config=self.config, auth=self.auth)

        # Test that successful initialization without cache, auto-assigns cache object.
        up = UploadManager(file=self.file, config=self.config, auth=self.auth, file_name=self.file_name)
        self.assertEqual(type(up.cache), Cache)

        # Test default value: multithreading=False.
        self.assertEqual(up.multithreading, False)

        # Test default value: workers=4.
        self.assertEqual(up.workers, 4)

        # Test default value: ignore_cache=False.
        self.assertEqual(up.ignore_cache, False)

        # Test default value: content_type=None.
        self.assertEqual(up.content_type, None)

        # Test default value: clear_cache=False.
        self.assertEqual(up.clear_cache, False)

        # Test default value: abort_on_fail=False.
        self.assertEqual(up.abort_on_fail, False)

        # Test default value: error="".
        self.assertEqual(up.error, "")

    @mock.patch("filelib.upload_manager.UploadManager.process_file")
    def test_add_file_calls_gen_file_index(self, process_file):
        """
        UploadManager.__init__ method must call process_file method
        """
        process_file.return_value = (self.file_name, self.file)
        UploadManager(file=self.file, config=self.config, auth=self.auth, file_name=self.file_name)
        process_file.assert_called_once()

    def test_process_file_value(self):
        """
        UploadManager.process_file method must return a tuple (file_name, file)
        file_name must be just the file name with directories stripped.
        """
        file_name = "/mydir/subdir/evendeeperdir/filename"
        file = self.file
        file_name, _ = UploadManager.process_file(file_name, file)
        self.assertEqual(file_name, "filename")

    def test_cache_methods(self):
        """
        UploadManager.has_cache must return a bool value.
        This is part of keeping track of upload progress of a given file.
        First time init: False
        Second time init: True
        `ignore_cache=True`: False

        """
        up = self.gen_up()
        # On init, cache must be empty
        self.assertEqual(up.has_cache(), False)
        with mock_httpx_request("post", response={}, headers=self.init_upload_201_res_headers):
            with mock.patch("filelib.UploadManager.single_thread_upload", new_callable=lambda: None):
                up = self.gen_up()
                up.upload()
                # when upload initialized, must have cache
                self.assertEqual(up.has_cache(), True)
                # Location must be in the cache.
                self.assertEqual(up.get_cache(up._CACHE_LOCATION_KEY),
                                 self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])
                # Must be able to set cache values
                cache_key, cache_val = "key", "yolo"
                up.set_cache(cache_key, cache_val)
                self.assertEqual(up.get_cache(cache_key), cache_val)
                # ignore_cache=True handles.
                up = self.gen_up(ignore_cache=True, cache=Cache(namespace="newnamespace", path=self.test_cache_path))
                # property must be set to True
                self.assertEqual(up.ignore_cache, True)
                # has_cache must be false after upload
                up.upload()
                self.assertEqual(up.has_cache(), False)
                # get_cache must return None
                self.assertEqual(up.get_cache(up._CACHE_LOCATION_KEY), None)
                # set_cache must return False
                self.assertEqual(up.set_cache(cache_key, cache_val), False)
                self.assertEqual(up.get_cache(cache_key), None)

    def test_get_file_size(self):
        """
        Test get_file_size
        Must return int
        Must be exact to the bytes of the content.
        """
        file = io.BytesIO(b"".join([bytes("i", "utf8") for _i in range(100)]))
        file_size = 100
        up = self.gen_up(file=file)
        self.assertEqual(up.get_file_size(), file_size)

    def test_calculate_part_count(self):
        """
        Must be able to calculate part count by chunk size.
        """
        file = io.BytesIO(b"".join([bytes("i", "utf8") for _i in range(550)]))
        with mock_httpx_request("post", response={}, headers=self.init_upload_201_res_headers):
            up = self.gen_up(file=file)
            up.UPLOAD_CHUNK_SIZE = 100
            part_count = 6
            self.assertEqual(up.calculate_part_count(), part_count)

    def test_initialize_upload(self):
        """
        UploadManager._initialize_upload
        Test that it set up necessary properties.
        """
        # Test it raises error if API response is not success.
        with mock_httpx_request("post", response=self.init_upload_400_res_json, status_code=400):
            up = self.gen_up()
            with self.assertRaises(FilelibAPIException):
                up.upload()
        # Test happy path
        with mock_httpx_request("post", response={}, headers=self.init_upload_201_res_headers):
            with mock.patch("filelib.UploadManager.single_thread_upload", new_callable=lambda: None):
                up = self.gen_up()
                # Fire _initialize_upload method
                up.upload()
                # Must upload method dependencies
                self.assertEqual(up._FILE_UPLOAD_URL, self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])
                self.assertEqual(up._FILE_UPLOAD_STATUS, UPLOAD_PENDING)
                self.assertEqual(up.MAX_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_MAX_CHUNK_SIZE_HEADER]))
                self.assertEqual(up.MIN_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_MIN_CHUNK_SIZE_HEADER]))
                self.assertEqual(up.UPLOAD_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_CHUNK_SIZE_HEADER]))
                self.assertEqual(type(up._UPLOAD_PART_NUMBER_SET), set)
                self.assertEqual(len(up._UPLOAD_PART_NUMBER_SET), up.calculate_part_count())
                # Must set cache for Location
                self.assertEqual(up.get_cache(up._CACHE_LOCATION_KEY), self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])
                # self.assertEqual(1, 3)

    def tearDown(self):
        # Remove Cache storage path after tests are done.
        shutil.rmtree(self.test_cache_path, ignore_errors=True)
