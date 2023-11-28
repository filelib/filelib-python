import io
import shutil
import string
from copy import deepcopy
from unittest import TestCase, mock
from uuid import uuid4

import httpx
from jmstorage import Cache

from filelib import FilelibConfig, UploadManager
from filelib.constants import (
    CONTENT_TYPE_HEADER,
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_XML,
    ERROR_CODE_HEADER,
    ERROR_MESSAGE_HEADER,
    FILE_UPLOAD_STATUS_HEADER,
    UPLOAD_CANCELLED,
    UPLOAD_CHUNK_SIZE_HEADER,
    UPLOAD_FAILED,
    UPLOAD_LOCATION_HEADER,
    UPLOAD_MAX_CHUNK_SIZE_HEADER,
    UPLOAD_MIN_CHUNK_SIZE_HEADER,
    UPLOAD_MISSING_PART_NUMBERS_HEADER,
    UPLOAD_PART_NUMBER_POSITION_HEADER,
    UPLOAD_PENDING,
    UPLOAD_STARTED
)
from filelib.exceptions import (
    ChunkUploadFailedError,
    FilelibAPIException,
    FileNameRequiredError
)
from tests.mocks import (
    GET_UPLOAD_STATUS_RESPONSE_BODY,
    DummyExecutor,
    mock_authentication,
    mock_request
)


class UploadManagerTestCase(TestCase):
    init_upload_201_res_headers = {
        UPLOAD_MAX_CHUNK_SIZE_HEADER: str(10000),
        UPLOAD_MIN_CHUNK_SIZE_HEADER: str(1000),
        UPLOAD_CHUNK_SIZE_HEADER: str(5000),
        UPLOAD_LOCATION_HEADER: f"https://testserver.nonexisting/api/upload/{str(uuid4())}"
    }

    # 10 parts assumption.
    init_get_req_success_headers = {
        FILE_UPLOAD_STATUS_HEADER: UPLOAD_STARTED,
        UPLOAD_MISSING_PART_NUMBERS_HEADER: "1,2,5",
        UPLOAD_PART_NUMBER_POSITION_HEADER: "10",
        UPLOAD_CHUNK_SIZE_HEADER: "1",
        UPLOAD_MAX_CHUNK_SIZE_HEADER: str(255),
        UPLOAD_MIN_CHUNK_SIZE_HEADER: str(55),
    }

    XML_ERROR_RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?><Error><Code>NoSuchUpload</Code><Message>The specified upload does not exist. The
        upload ID may be invalid, or the upload may have been aborted or
        completed.</Message><UploadId>4B6JVR7779xj7bbbbbbb</UploadId><RequestId>V0NT9TYPPPHAPV6F</RequestId><HostId
        >MwPflnCyGE7DKM8xeRU112zzXDAwznUMvgQnNu4gaFHnFm2QpQKcoJi8ZbGqYs6cE0jzD1cE2Kc=</HostId></Error>"""

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

    def test_init(self):
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

        # Upload behaviour
        self.assertEqual(up.is_direct_upload, False)
        self.assertEqual(up._FILE_SIZE, up.get_file_size())
        self.assertEqual(up._FILE_ENTITY_URL, None)
        self.assertEqual(up._FILE_ENTITY_URL_MAP, None)

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

    def test_process_file(self):
        """
        UploadManager.process_file method must return a tuple (file_name, file)
        file_name must be just the file name with directories stripped.
        """
        file_name = "/mydir/subdir/evendeeperdir/filename"
        file = self.file
        file_name, _ = UploadManager.process_file(file_name, file)
        self.assertEqual(file_name, "filename")

    # get_cache
    # set_cache
    # delete_cache
    # truncate_cache
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

        # delete cache
        up.set_cache("hello", "world")
        self.assertEqual(up.get_cache("hello"), "world")
        up.delete_cache("hello")
        self.assertEqual(up.get_cache("hello"), None)

        with mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers):
            with mock.patch("filelib.UploadManager.single_thread_upload", new_callable=lambda: None):
                up = self.gen_up()
                up.upload()
                # when upload initialized, must have cache
                self.assertEqual(up.has_cache(), True)
                # Location must be in the cache.
                self.assertEqual(up.get_cache(up._CACHE_ENTITY_KEY),
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
                self.assertEqual(up.get_cache(up._CACHE_ENTITY_KEY), None)
                # set_cache must return False
                self.assertEqual(up.set_cache(cache_key, cache_val), False)
                self.assertEqual(up.get_cache(cache_key), None)

    # get_cache_namespace
    def test_get_cache_namespace(self):
        """
        This is used when cache=None and UploadManager creates cache itself.
        It needs to generate a namespace from file name and upto 1000 bytes of content
        must return integer
        """
        f1, f2 = io.BytesIO(bytes(string.ascii_letters, "utf8")), io.BytesIO(bytes(string.digits, "utf8"))
        f1_name, f2_name = "f1", "f2"
        up1 = self.gen_up(file=f1, file_name=f1_name)
        up2 = self.gen_up(file=f2, file_name=f2_name)
        self.assertTrue(type(up1.get_cache_namespace()) is int)
        self.assertTrue(type(up2.get_cache_namespace()) is int)
        self.assertNotEqual(up1.get_cache_namespace(), up2.get_cache_namespace())

    def test_get_chunk(self):
        """
        UploadManager.get_chunk method must return a byte object that belongs to a given part number.
        """
        data = string.ascii_letters
        file = io.BytesIO(bytes(data, "utf8"))
        up = self.gen_up(file=file)
        up.UPLOAD_CHUNK_SIZE = 1
        for part_num, chunk in enumerate(data):
            b_chunk = up.get_chunk(part_number=part_num + 1)
            self.assertEqual(bytes(chunk, "utf8"), b_chunk)

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
        with mock_request("post", response={}, headers=self.init_upload_201_res_headers):
            up = self.gen_up(file=file)
            up.UPLOAD_CHUNK_SIZE = 100
            part_count = 6
            self.assertEqual(up.calculate_part_count(), part_count)

    def test_fetch_upload_status(self):
        """
        When there is a cache of a file that was previously started/completed
        it must fetch from the server and assign part numbers if not completed.
        If completed, it must resign

        It must call the following methods:
            * `get_cache`
            * `delete_cache` if 404
            * `set_cache` on success
            * `init_upload` if 404
            * raise FilelibAPIException if not success
            * assign `_FILE_ENTITY_URL` to value
            * `_set_upload_params`

        """
        file_name, file = "upload_status.txt", io.BytesIO(b"".join([b"i" for i in range(10)]))
        up = self.gen_up(file_name=file_name, file=file)
        up.UPLOAD_CHUNK_SIZE = 1
        # Ensure it is single_thread_upload
        self.assertEqual(up.multithreading, False)
        # when there is no cache, it must call, init_upload
        self.assertEqual(up.has_cache(), False)
        # It must fail with value error when there is no cache.

        with self.assertRaises(ValueError):
            up.fetch_upload_status()
        url = "http://testserver/api/upload/1234"
        up.set_cache(up._CACHE_ENTITY_KEY, url)

        # Other error response must raise FilelibAPiException
        with mock_request("get", status_code=400):
            with self.assertRaises(FilelibAPIException):
                up.fetch_upload_status()

        # 404 response must call `init_upload`
        # 404 response must call `delete_cache`
        with mock_request("get", status_code=404):
            with mock.patch("filelib.UploadManager.init_upload") as init_up:
                with mock.patch("filelib.UploadManager.delete_cache", side_effect=up.delete_cache) as del_cache:
                    up.fetch_upload_status()
                    init_up.assert_called_once()
                    del_cache.assert_called_once()
                    self.assertEqual(up.has_cache(), False)

        # success must assign the following values
        up.set_cache(up._CACHE_ENTITY_KEY, url)
        with mock_request("get", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_get_req_success_headers):
            with mock.patch("filelib.UploadManager._set_upload_params", side_effect=up._set_upload_params) as setup_params:
                with mock.patch("filelib.UploadManager._parse_headers", side_effect=up._parse_headers) as parse_headers:

                    up.fetch_upload_status()
                    setup_params.assert_called_once()
                    parse_headers.assert_called_once()
                    self.assertEqual(up._FILE_ENTITY_URL, url)
                    self.assertEqual(up.get_cache(up._CACHE_ENTITY_KEY), url)
                    # Header values must match assigned values
                    self.assertEqual(up.get_upload_status(), self.init_get_req_success_headers[FILE_UPLOAD_STATUS_HEADER])
                    # Test missing parts numbers are in the part number set
                    expect_part_num_set = set(map(int, self.init_get_req_success_headers[UPLOAD_MISSING_PART_NUMBERS_HEADER].split(',')))
                    self.assertEqual(up.get_upload_part_number_set(), expect_part_num_set)
                    # Test that last prt number uploaded is not in the set.
                    self.assertNotIn(int(self.init_get_req_success_headers[UPLOAD_PART_NUMBER_POSITION_HEADER]), up.get_upload_part_number_set())
                    # Upload chunk size must be assigned to provided value.
                    self.assertEqual(up.UPLOAD_CHUNK_SIZE, int(self.init_get_req_success_headers[UPLOAD_CHUNK_SIZE_HEADER]))
                    self.assertEqual(up.MAX_CHUNK_SIZE, int(self.init_get_req_success_headers[UPLOAD_MAX_CHUNK_SIZE_HEADER]))
                    self.assertEqual(up.MIN_CHUNK_SIZE, int(self.init_get_req_success_headers[UPLOAD_MIN_CHUNK_SIZE_HEADER]))

    def test_parse_headers(self):
        """
        This method assigns properties to UploadManager after a successful request to Filelib API
        Must Assign the following:
            * MAX_CHUNK_SIZE
            * MIN_CHUNK_SIZE
            * UPLOAD_CHUNK_SIZE
            * _UPLOAD_PART_NUMBER_SET
            * _FILE_ENTITY_URL if status is UPLOAD_STARTED
        Must call the following:
            * set_upload_status
            * set_cache
        """
        up = self.gen_up()

        headers = deepcopy(self.init_upload_201_res_headers)
        headers[FILE_UPLOAD_STATUS_HEADER] = UPLOAD_PENDING
        res_headers = httpx.Headers(headers=headers)
        up._parse_headers(res_headers)
        self.assertEqual(up.MAX_CHUNK_SIZE, int(headers[UPLOAD_MAX_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.MIN_CHUNK_SIZE, int(headers[UPLOAD_MIN_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.UPLOAD_CHUNK_SIZE, int(headers[UPLOAD_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.get_upload_status(), headers[FILE_UPLOAD_STATUS_HEADER])

        # UPLOAD_PENDING  `_UPLOAD_PART_NUMBER_SET` must be full range: 1-n
        self.assertEqual(type(up._UPLOAD_PART_NUMBER_SET), set)
        self.assertEqual({i for i in range(1, up.calculate_part_count() + 1)}, up.get_upload_part_number_set())

        # UPLOAD_STARTED `_UPLOAD_PART_NUMBER_SET` must contain missing part numbers and the range from the last uploaded part.
        headers = deepcopy(self.init_get_req_success_headers)
        headers[FILE_UPLOAD_STATUS_HEADER] = UPLOAD_STARTED
        up = self.gen_up()
        res_headers = httpx.Headers(headers=headers)
        with mock.patch("filelib.UploadManager.set_cache") as _set_cache:
            with mock.patch("filelib.UploadManager.set_upload_status", side_effect=up.set_upload_status) as _set_upload_status:
                up._parse_headers(res_headers)
                _set_cache.assert_called_once()
                _set_upload_status.assert_called_once()

        # MUST still assign the values needed
        self.assertEqual(up.MAX_CHUNK_SIZE, int(headers[UPLOAD_MAX_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.MIN_CHUNK_SIZE, int(headers[UPLOAD_MIN_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.UPLOAD_CHUNK_SIZE, int(headers[UPLOAD_CHUNK_SIZE_HEADER]))
        self.assertEqual(up.get_upload_status(), headers[FILE_UPLOAD_STATUS_HEADER])
        # UPLOAD_PENDING `_UPLOAD_PART_NUMBER_SET` must be full range: 1-n
        self.assertEqual(type(up._UPLOAD_PART_NUMBER_SET), set)
        # missing part numbers must be in
        part_number_set = {i for i in map(int, headers[UPLOAD_MISSING_PART_NUMBERS_HEADER].split(","))}
        self.assertTrue(part_number_set <= up.get_upload_part_number_set())
        part_number_set.update(range(int(headers[UPLOAD_PART_NUMBER_POSITION_HEADER]) + 1, up.calculate_part_count() + 1))
        self.assertEqual(up.get_upload_part_number_set(), part_number_set)

    def test_get_create_payload(self):
        """
        This method will provide a dict with payload for `init_upload`
        """
        up = self.gen_up()
        payload = up._get_create_payload()
        self.assertEqual(type(payload), dict)
        self.assertTrue("file_name" in payload)
        self.assertTrue("file_size" in payload)
        self.assertTrue("mimetype" in payload)

    def test_init_upload(self):
        """
        Gets called when `UploadManager.upload` method is called.

        * Must raise FilelibAPIException if not success.
        * Must check if there is cache
        * Must call `fetch_upload_status` if there is cache
        * Must call `_set_upload_params` method.
        * Must call `_parse_headers` method.
        * Must call `set_cache` method.

        * MUST ASSIGN the following:
            * is_direct_upload if direct upload.
            * _FILE_ENTITY_URL.
            * _FILE_ENTITY_URL_MAP if direct upload.

        """
        # Test it raises error if API response is not success.
        with mock_request("post", response=self.init_upload_400_res_json, status_code=400):
            up = self.gen_up()
            with self.assertRaises(FilelibAPIException):
                up.upload()
        # Test happy path
        up = self.gen_up()
        mock_has_cache = mock.patch("filelib.UploadManager.has_cache", side_effect=up.has_cache)
        mock_parse_headers = mock.patch("filelib.UploadManager._parse_headers", side_effect=up._parse_headers)

        mock_post_req = mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers)
        with mock_post_req:
            with mock_has_cache as _has_cache:
                with mock_parse_headers as _parse_headers:
                    with mock.patch("filelib.UploadManager.single_thread_upload", new=lambda x: None):
                        # Fire init_upload method
                        up.upload()
                        _has_cache.assert_called_once()
                        _parse_headers.assert_called_once()
                        # Must upload method dependencies
                        self.assertEqual(up._FILE_ENTITY_URL, self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])
                        self.assertEqual(up.is_direct_upload, True)
                        self.assertEqual(up._FILE_ENTITY_URL_MAP, GET_UPLOAD_STATUS_RESPONSE_BODY["data"]["upload_urls"])
                        self.assertEqual(up.get_upload_status(), UPLOAD_PENDING)
                        self.assertEqual(up.MAX_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_MAX_CHUNK_SIZE_HEADER]))
                        self.assertEqual(up.MIN_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_MIN_CHUNK_SIZE_HEADER]))
                        self.assertEqual(up.UPLOAD_CHUNK_SIZE, int(self.init_upload_201_res_headers[UPLOAD_CHUNK_SIZE_HEADER]))
                        self.assertEqual(type(up._UPLOAD_PART_NUMBER_SET), set)
                        self.assertEqual(len(up._UPLOAD_PART_NUMBER_SET), up.calculate_part_count())
                        # Must set cache for Location
                        self.assertEqual(up.get_cache(up._CACHE_ENTITY_KEY), self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])
                        # make sure cache has value now
                        self.assertEqual(up.has_cache(), True)

        # Now there must be cache, and it must call fetch_upload_status since cache exists
        mock_fet_up = mock.patch("filelib.UploadManager.fetch_upload_status", return_value=None)
        with mock_fet_up as _fetch_up_stat:
            up.upload()
            _fetch_up_stat.assert_called_once()

    def test_set_upload_params(self):
        """
        Test `UploadManager._set_upload_params` method
        This assigns values to UploadManager object for upload to take place.
        MUST CALL THE FOLLOWING:
        * _parse_headers
        * set_cache

        MUST ASSIGN THE FOLLOWING
        * _FILE_ENTITY_URL
        * _FILE_ENTITY_URL_MAP
        * is_direct_upload

        """
        up = self.gen_up()
        post_headers = self.init_upload_201_res_headers
        post_response = GET_UPLOAD_STATUS_RESPONSE_BODY
        post_mock = mock_request("post", status_code=201, response=post_response, headers=post_headers)
        mock_parse_headers = mock.patch("filelib.UploadManager._parse_headers", side_effect=up._parse_headers)
        mock_set_cache = mock.patch("filelib.UploadManager.set_cache", side_effect=up.set_cache)

        with post_mock:
            with mock_parse_headers as _parse_headers:
                with mock_set_cache as _set_cache:
                    with mock.patch("filelib.UploadManager._set_upload_params", side_effect=up._set_upload_params) as _set_up_params:
                        up.init_upload()
                        _set_up_params.assert_called_once()
                        _parse_headers.assert_called_once()
                        self.assertTrue(_set_cache.call_count > 0)
                        # must assign is_direct_upload
                        self.assertEqual(up.is_direct_upload, True)
                        self.assertEqual(up._FILE_ENTITY_URL, post_headers[UPLOAD_LOCATION_HEADER])
                        self.assertEqual(up._FILE_ENTITY_URL_MAP, post_response["data"]["upload_urls"])

    def test_upload_chunk(self):
        """
        Test `UploadManager.upload_chunk` method

        Must call the following
        * get_chunk

        * MUST call UploadErrorParser if upload fails.
        * MUST raise ChunkUploadFailedError if upload fails.
        * MUST call log_url if is_direct_upload is True
        * MUST upload _FILE_ENTITY_URL_MAP if is_direct_upload is True

        ** is_direct_upload
            * if True, upload must happen to the provided url map _FILE_ENTITY_URL_MAP
            * if false, upload must be with a patch request to Filelib API
        """

        up = self.gen_up()

        # Must fail with error response from api
        error_headers = {
            ERROR_MESSAGE_HEADER: "test_upload_chunk_error",
            ERROR_CODE_HEADER: "TEST_UPLOAD_CHUNK_CODE"
        }
        method = GET_UPLOAD_STATUS_RESPONSE_BODY["data"]["upload_urls"]["1"]["method"]
        with mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers):
            up.init_upload()
            # Filelib Upload: is_direct_upload=True

            error_headers[CONTENT_TYPE_HEADER] = CONTENT_TYPE_XML
            with mock.patch("filelib.parsers.AWSErrorParser.format") as _upload_parser:
                with mock_request(method, status_code=400, response=self.XML_ERROR_RESPONSE, headers=error_headers):
                    self.assertEqual(up.is_direct_upload, True)
                    with self.assertRaises(ChunkUploadFailedError):
                        up.upload_chunk(1)
                    _upload_parser.assert_called_once()

            # Filelib Upload: is_direct_upload=False
            up.is_direct_upload = False
            error_headers[CONTENT_TYPE_HEADER] = CONTENT_TYPE_JSON
            with mock_request("patch", status_code=400, response=None, headers=error_headers):
                self.assertEqual(up.is_direct_upload, False)
                with self.assertRaises(ChunkUploadFailedError):
                    up.upload_chunk(1)

        mock_get_chunk = mock.patch("filelib.UploadManager.get_chunk", side_effect=up.get_chunk)

        # Test response must not raise any error
        with mock_get_chunk as _get_chunk:
            with mock_request("patch", status_code=201, response=None) as _upload_req:
                up.upload_chunk(1)
                _get_chunk.assert_called_once()
                upload_url, = _upload_req.call_args.args
                self.assertEqual(upload_url, self.init_upload_201_res_headers[UPLOAD_LOCATION_HEADER])

        # Direct upload response must not raise any error
        up.is_direct_upload = True
        with mock_get_chunk as _get_chunk:
            with mock_request(method, status_code=201, response=None) as _upload_req:
                # mock log_url
                with mock_request("post", status_code=201, response=None) as log_req:
                    up.upload_chunk(1)
                    _get_chunk.assert_called_once()
                    # ('http://testserver/file_id/1/log-part-number-upload/',)
                    log_url, = log_req.call_args.args
                    upload_url, = _upload_req.call_args.args
                    self.assertEqual(upload_url, GET_UPLOAD_STATUS_RESPONSE_BODY["data"]["upload_urls"]["1"]["url"])
                    self.assertEqual(log_url, GET_UPLOAD_STATUS_RESPONSE_BODY["data"]["upload_urls"]["1"]["log_url"])

    def test_single_thread_upload(self):
        """
        Ensure single_thread_upload method calls the following methods:
        set_upload_status x 2
        get_upload_part_number_set
        upload_chunk
        """
        with mock.patch("filelib.UploadManager.set_upload_status") as up_stat_func:
            with mock.patch("filelib.UploadManager.get_upload_part_number_set") as get_up_p_n_set:
                with mock.patch("filelib.UploadManager.upload_chunk") as up_chunk:
                    get_up_p_n_set.return_value = {1}
                    up = self.gen_up()
                    up.single_thread_upload()
                    # set_upload_status must be called twice
                    self.assertEqual(up_stat_func.call_count, 2)

                    # get_upload_part_number_set must be called once
                    get_up_p_n_set.assert_called_once()

                    # upload_chunk must be called once
                    up_chunk.assert_called_once()

    def test_multithread_upload(self):
        """
        Test multithread_upload method
        it must call the following methods:
            1. set_upload_status x 2
            2. get_upload_part_number_set
            3. concurrent.futures.ThreadPoolExecutor
            4. upload_chunk
        """

        with mock.patch("concurrent.futures.ThreadPoolExecutor.__enter__", return_value=DummyExecutor()) as executor:
            with mock.patch("filelib.UploadManager.set_upload_status") as up_stat_func:
                with mock.patch("filelib.UploadManager.get_upload_part_number_set") as get_up_p_n_set:
                    with mock.patch("filelib.UploadManager.upload_chunk") as up_chunk:
                        get_up_p_n_set.return_value = {1}
                        up = self.gen_up(multithreading=True)
                        up.multithread_upload()
                        self.assertEqual(up_stat_func.call_count, 2)

                        # get_upload_part_number_set must be called once
                        get_up_p_n_set.assert_called_once()

                        # concurrent.futures.ThreadPoolExecutor must be called once
                        executor.assert_called_once()

                        # upload_chunk must be called once
                        up_chunk.assert_called_once()
        # workers must be validated.
        # less than 1 must raise error if not None
        with self.assertRaises(ValueError):
            up = self.gen_up(workers=0)
            up.multithread_upload()

    def test_cleanup(self):
        """
        cleanup method must set file property to None
        """
        up = self.gen_up()
        # Make sure it exists first
        self.assertEqual(up.file, self.file)
        up.cleanup()
        self.assertEqual(up.file, None)

    def test_cancel(self):
        """
        cancel method must initiate a request to Filelib API
        Success:
            set status to cancelled
        Error:
            raise Filelib Api Exception
        """
        # Must fail with error response from api
        error_headers = {
            ERROR_MESSAGE_HEADER: "test_cancel_upload_error",
            ERROR_CODE_HEADER: "TEST_CANCEL_UPLOAD_ERROR_CODE"
        }
        up = self.gen_up()
        with mock_request("delete", status_code=400, response=None, headers=error_headers):
            with self.assertRaises(FilelibAPIException):
                up.cancel()

        # Success set status to UPLOAD_CANCELLED
        with mock_request("delete", status_code=204) as req:
            up.cancel()
            self.assertEqual(up.get_upload_status(), UPLOAD_CANCELLED)
            req.assert_called_once()

    def test_get_error(self):
        """
        Ensure this method is defined in UploadManager and returns error property value
        """
        up = self.gen_up()
        err_message = "test_error"
        up.error = err_message
        self.assertEqual(up.get_error(), err_message)

    def test_get_upload_part_number_set(self):
        """
        This will return a set containing all part numbers that will be uploaded.
        """
        up = self.gen_up()
        with mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers):
            up.init_upload()
            self.assertEqual({1}, up.get_upload_part_number_set())

    def test_get_upload_status_fails(self):
        """
        HEAD request to server with a 404 response must call init_upload.
        HEAD request any other error must terminate.
        It must also clear cache for that file.
        """
        up = self.gen_up()
        with mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers):
            with mock.patch("filelib.UploadManager.single_thread_upload", new=lambda: None):
                # fire init_upload
                up.upload()

                # Fail must terminate.
                error_headers = {
                    ERROR_MESSAGE_HEADER: "test_error",
                    ERROR_CODE_HEADER: "TEST_ERROR_CODE"
                }
                with mock_request("get", status_code=400, response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=error_headers):
                    try:

                        up.fetch_upload_status()
                    except FilelibAPIException as e:
                        err_msg, status_code, error_code = e.message, e.code, e.error_code
                        self.assertEqual(err_msg, error_headers[ERROR_MESSAGE_HEADER])
                        self.assertEqual(status_code, 400)
                        self.assertEqual(error_code, error_headers[ERROR_CODE_HEADER])

                # Trigger HEAD with fetch_upload_status
                with mock_request("get", status_code=404, response=None):
                    with mock.patch("filelib.upload_manager.UploadManager.init_upload") as init_upload:
                        up.fetch_upload_status()
                        init_upload.assert_called_once()
                        self.assertEqual(up.get_cache(up._CACHE_ENTITY_KEY), None)

    def test_upload_method(self):
        """
        Test `UploadManager.upload` method

        Must call the following

        * init_upload
        * get_upload_part_number_set
        * multithread_upload if multithreading
        * single_thread_upload if not multithreading
        * set_upload_status UPLOAD_FAILED on fail. UPLOAD_COMPLETED otherwise.
        * cancel if abort_on_fail=True
        * truncate_cache if clear_cache=True

        """

        post_req = mock_request("post", response=GET_UPLOAD_STATUS_RESPONSE_BODY, headers=self.init_upload_201_res_headers)
        get_up_part_n_set = mock.patch("filelib.UploadManager.get_upload_part_number_set")
        multithread_upload = mock.patch("filelib.UploadManager.multithread_upload")
        single_thread_upload = mock.patch("filelib.UploadManager.single_thread_upload")
        cancel = mock.patch("filelib.UploadManager.cancel")
        truncate_cache = mock.patch("filelib.UploadManager.truncate_cache")
        get_up_part_n_set.return_value = {1}

        # Initialize instance
        with post_req:
            up = self.gen_up(multithreading=False, abort_on_fail=True, clear_cache=True)
            init_upload = mock.patch("filelib.UploadManager.init_upload", side_effect=up.init_upload)
            with get_up_part_n_set as get_up_part_num:
                with init_upload as init:
                    # Single thread upload
                    up.multithreading = False
                    with single_thread_upload as single_thread_upload:
                        up.upload()
                        init.assert_called_once()
                        get_up_part_num.assert_called_once()
                        single_thread_upload.assert_called_once()
                        get_up_part_num.assert_called_once()
                    # multithread upload
                    up.truncate_cache()
                    with multithread_upload as multi_upload:
                        up.multithreading = True
                        up.upload()

                        multi_upload.assert_called_once()

                    # Trigger Fail
                    up.truncate_cache()
                    error_msg = "error_msg"

                    def se():
                        raise Exception(error_msg)

                    with mock.patch("filelib.UploadManager.multithread_upload", side_effect=se):
                        with cancel as cancel:
                            with truncate_cache as truncate:
                                up.upload()
                                cancel.assert_called_once()
                                truncate.assert_called_once()
                                self.assertEqual(up.get_error(), error_msg)
                                self.assertEqual(up.get_upload_status(), UPLOAD_FAILED)

    def test_get_upload_status(self):
        """
        Test that it returns the value of `_FILE_UPLOAD_STATUS`
        """
        up = self.gen_up()
        self.assertEqual(up.get_upload_status(), UPLOAD_PENDING)

    def tearDown(self):
        # Remove Cache storage path after tests are done.
        shutil.rmtree(self.test_cache_path, ignore_errors=True)
