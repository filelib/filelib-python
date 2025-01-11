import concurrent.futures
import math
import os.path
import typing
import zlib

import httpx
from jmstorage import Cache

from . import Authentication
from .config import FilelibConfig
from .constants import (
    FILE_UPLOAD_STATUS_HEADER,
    FILE_UPLOAD_URL,
    UPLOAD_CANCELLED,
    UPLOAD_CHUNK_SIZE_HEADER,
    UPLOAD_COMPLETED,
    UPLOAD_FAILED,
    UPLOAD_LOCATION_HEADER,
    UPLOAD_MAX_CHUNK_SIZE_HEADER,
    UPLOAD_MIN_CHUNK_SIZE_HEADER,
    UPLOAD_MISSING_PART_NUMBERS_HEADER,
    UPLOAD_PART_CHUNK_NUM_HEADER,
    UPLOAD_PART_NUMBER_POSITION_HEADER,
    UPLOAD_PENDING,
    UPLOAD_STARTED
)
from .exceptions import (
    ChunkUploadFailedError,
    FilelibAPIException,
    NoChunksToUpload
)
from .parsers import UploadErrorParser
from .utils import parse_api_err, process_file as proc_file


class UploadManager:
    MB = 2 ** 20
    MAX_CHUNK_SIZE = 64 * MB
    MIN_CHUNK_SIZE = 5 * MB

    # This value can be changed if server responds with previous uploads.
    UPLOAD_CHUNK_SIZE = MAX_CHUNK_SIZE

    _FILE_UPLOAD_STATUS = UPLOAD_PENDING
    # This represents what part numbers to upload.
    _UPLOAD_PART_NUMBER_SET = set()

    # Key name for storing unique file URL
    _CACHE_ENTITY_KEY = "LOCATION"

    def __init__(
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
    ):
        self.file_name, self.file = self.process_file(file_name, file)
        self.config = config
        self.auth = auth
        self.multithreading = multithreading
        self.workers = workers

        # Filelib API response based params
        self.is_direct_upload = False
        self._FILE_SIZE: typing.Optional[int, None] = None
        self._FILE_ENTITY_URL: typing.Optional[str, None] = None
        self._FILE_ENTITY_URL_MAP = None

        # Allow the user to start over an upload from scratch
        self.ignore_cache = ignore_cache
        self.cache = cache or Cache(namespace=str(self.get_cache_namespace()), path="./subdir")
        self.content_type = content_type
        self.clear_cache = clear_cache
        self.abort_on_fail = abort_on_fail
        # Set Error prop
        self.error = ""

    @staticmethod
    def process_file(file_name, file):
        return proc_file(file_name, file)

    def has_cache(self):
        # `ignore_cache` setting must return false.
        if self.ignore_cache:
            return False
        return self.cache.get(self._CACHE_ENTITY_KEY) is not None

    def get_cache(self, key):
        return self.cache.get(key)

    def set_cache(self, key, value):
        if self.ignore_cache:
            return False
        self.cache.set(key, value)

    def delete_cache(self, key):
        return self.cache.delete(key)

    def truncate_cache(self):
        self.cache.truncate()

    def get_cache_namespace(self):
        """
        Generate checksum of the first 1000 bytes
        """
        return zlib.crc32(self.get_chunk(1, 1000) + bytes(self.file_name, "utf8"))

    def get_chunk(self, part_number, chunk_size=None):
        """
        Get chunk corresponding to the part number provided
        chunk_size to overwrite how to read for chunk.
        """
        _chunk_size = chunk_size or self.UPLOAD_CHUNK_SIZE
        seek_start = (part_number - 1) * _chunk_size
        file_size = self.get_file_size()
        # Prevent reading from further than last byte.
        if seek_start + _chunk_size > file_size:
            _chunk_size = file_size - seek_start
        self.file.seek(seek_start)
        return self.file.read(_chunk_size)

    def get_file_size(self) -> int:
        if not self._FILE_SIZE:
            self._FILE_SIZE = self.file.seek(0, os.SEEK_END)
            self.file.seek(0)
        return self._FILE_SIZE

    def calculate_part_count(self) -> int:
        """
        Calculate how many parts file will be chunked into by size/chunk_size
        """
        return math.ceil(self.get_file_size() / self.UPLOAD_CHUNK_SIZE)

    def fetch_upload_status(self):
        """
        If we have a reference for the current file being processed
        we can check from the server how much progress has been made.
        """
        file_url = self.get_cache(self._CACHE_ENTITY_KEY)
        if not file_url:
            raise ValueError("No file url to get status")
        with httpx.Client() as client:
            req = client.get(file_url, headers=self.auth.to_headers())
            # IF 404, means that our cache is out of sync
            # Re-initialize upload.
            if req.status_code == 404:
                self.delete_cache(self._CACHE_ENTITY_KEY)
                return self.init_upload(is_retry=True)
            if not req.is_success:
                raise FilelibAPIException(*parse_api_err(req))
            self._FILE_ENTITY_URL = file_url
            self._set_upload_params(req)

    def _parse_headers(self, headers: httpx.Headers) -> None:
        """
        Centralize assigning values to properties that are needed while uploading.
        :param headers: dict  headers: dict of headers values provided from Filelib API
        """

        upload_status = headers.get(FILE_UPLOAD_STATUS_HEADER) or self._FILE_UPLOAD_STATUS
        self.MAX_CHUNK_SIZE = int(headers.get(UPLOAD_MAX_CHUNK_SIZE_HEADER) or self.MAX_CHUNK_SIZE)
        self.MIN_CHUNK_SIZE = int(headers.get(UPLOAD_MIN_CHUNK_SIZE_HEADER) or self.MIN_CHUNK_SIZE)
        self.UPLOAD_CHUNK_SIZE = int(headers.get(UPLOAD_CHUNK_SIZE_HEADER, self.MAX_CHUNK_SIZE))
        self.set_upload_status(upload_status)

        if upload_status == UPLOAD_STARTED:

            missing_part_numbers = headers.get(UPLOAD_MISSING_PART_NUMBERS_HEADER)
            if missing_part_numbers:
                # values seperated by comma: "1,2,3,4,5"
                missing_part_numbers = map(int, missing_part_numbers.split(","))
                self._UPLOAD_PART_NUMBER_SET.update(missing_part_numbers)
            last_part_number_uploaded = headers.get(UPLOAD_PART_NUMBER_POSITION_HEADER)
            if last_part_number_uploaded:
                # exclude last part number that is uploaded.
                rest = range(int(last_part_number_uploaded) + 1, self.calculate_part_count() + 1)
                self._UPLOAD_PART_NUMBER_SET.update(rest)
        if upload_status == UPLOAD_PENDING:
            self._FILE_ENTITY_URL = headers.get(UPLOAD_LOCATION_HEADER)
            self._UPLOAD_PART_NUMBER_SET = set(range(1, self.calculate_part_count() + 1))
        # Store file url
        self.set_cache(self._CACHE_ENTITY_KEY, self._FILE_ENTITY_URL)

    def _get_create_payload(self) -> dict:
        return {
            "file_name": self.file_name,
            "file_size": self.get_file_size(),
            "mimetype": self.content_type
        }

    def init_upload(self, is_retry=False):
        """
        *** If there is a cache of the current file, fetch info from Filelib API
        Create entity on Filelib API for the given file.
        Filelib API will provide file-object-url
        Filelib API will provide upload url to send the chunks to.
        Filelib api might provide log url if direct upload can be achieved to prevent data loss.

        """
        if not self.ignore_cache and not is_retry and self.has_cache():
            return self.fetch_upload_status()

        headers = self.auth.to_headers()
        headers.update(self.config.to_headers())
        with httpx.Client() as client:
            req = client.post(FILE_UPLOAD_URL, data=self._get_create_payload(), headers=headers)
            if not req.is_success:
                raise FilelibAPIException(*parse_api_err(req))
            self._set_upload_params(req)

    def _set_upload_params(self, response: httpx.Response):
        data = response.json()['data'] if response.request.method.lower() in ["post", "get"] else {}
        headers = response.headers
        self._parse_headers(headers)
        if data:
            is_direct_upload = data.get("is_direct_upload", False)
            self.is_direct_upload = is_direct_upload
            upload_urls: typing.Mapping[str, dict] = data.get("upload_urls")
            if upload_urls:
                self._FILE_ENTITY_URL_MAP = upload_urls
        self.set_cache(self._CACHE_ENTITY_KEY, self._FILE_ENTITY_URL)

    def upload_chunk(self, part_number):
        """
        Send the chunk that belongs to the provided part number to Filelib API
        """
        chunk = self.get_chunk(part_number)
        headers = self.auth.to_headers()
        headers[UPLOAD_PART_CHUNK_NUM_HEADER] = str(part_number)
        headers[UPLOAD_CHUNK_SIZE_HEADER] = str(self.UPLOAD_CHUNK_SIZE)
        # Must raise error if API response is not success
        with httpx.Client() as client:
            # self.is_direct_upload = False
            method = client.patch
            upload_url = self._FILE_ENTITY_URL
            log_url = None
            platform = None
            # If direct upload possible, get the new method, URL, and log_url
            if self.is_direct_upload:
                platform = self._FILE_ENTITY_URL_MAP[str(part_number)]["platform"]
                method = getattr(client, self._FILE_ENTITY_URL_MAP[str(part_number)]["method"])
                upload_url = self._FILE_ENTITY_URL_MAP[str(part_number)]["url"]
                log_url = self._FILE_ENTITY_URL_MAP[str(part_number)]["log_url"]

            _headers = headers if not self.is_direct_upload else {}
            req = method(upload_url, content=chunk, headers=_headers)
            if not req.is_success:
                parser = UploadErrorParser(response=req, platform=platform)
                error = parser.format()
                raise ChunkUploadFailedError(*error)
            # send log if successful
            if log_url:
                client.post(log_url, headers=headers)

    def single_thread_upload(self):
        self.set_upload_status(UPLOAD_STARTED)
        for _part_number in self.get_upload_part_number_set():
            self.upload_chunk(_part_number)
        self.set_upload_status(UPLOAD_COMPLETED)

    def multithread_upload(self):
        self.set_upload_status(UPLOAD_STARTED)

        # Upload the highest part number last(out of multithread) so server can decide to mark file completed.
        part_nums = list(self.get_upload_part_number_set())
        last_part_number = max(part_nums)
        part_nums.remove(last_part_number)

        # Python3.8+ max_workers=None behaves differently from max_workers=<int>
        # Ref: https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
        workers = self.workers
        if workers is not None and workers < 1:
            raise ValueError("""
            Multithreading worker requires at least one worker or it must be None.
            Worker value provided: %d
            """ % workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Start the load operations and mark each future with its URL
            _pn_chunk = {executor.submit(self.upload_chunk, pn): pn for pn in part_nums}
            for _processed_chunk in concurrent.futures.as_completed(_pn_chunk):
                # Can access the completed part number as below if we need to.
                # completed_part_number = _pn_chunk[_processed_chunk]
                try:
                    _processed_chunk.result()
                except Exception as exc:
                    self.error = str(exc)
        self.upload_chunk(last_part_number)
        self.set_upload_status(UPLOAD_COMPLETED)

    def cleanup(self):
        # so this works when used in a process.
        self.file = None

    def cancel(self):
        """
        Abort the upload and the server will cancel the upload operation
        and will delete all previously uploaded parts.
        """
        with httpx.Client() as client:
            req = client.delete(self._FILE_ENTITY_URL, headers=self.auth.to_headers())
            if not req.is_success:
                raise FilelibAPIException(*parse_api_err(req))
            self.set_upload_status(UPLOAD_CANCELLED)

    def get_error(self):
        return self.error

    def get_upload_part_number_set(self):
        """
        return a set of part numbers that is waiting to be uploaded.
        """
        return self._UPLOAD_PART_NUMBER_SET

    def upload(self):
        """
        Upload file object to Filelib API
        """
        self.init_upload()
        # return
        try:

            if not self.get_upload_part_number_set():
                raise NoChunksToUpload("File `%s` does not have any parts to upload.", self.file_name)

            if self.multithreading:
                self.multithread_upload()
            else:
                self.single_thread_upload()
        except NoChunksToUpload:
            if self.get_upload_status() != UPLOAD_COMPLETED:
                raise
            # Safely exit otherwise
        except Exception as e:
            self.set_upload_status(UPLOAD_FAILED)
            self.error = str(e)
            if self.abort_on_fail:
                self.cancel()
        # Clear cache after successful upload is opted in
        if self.clear_cache:
            self.truncate_cache()

    def get_upload_status(self):
        return self._FILE_UPLOAD_STATUS

    def set_upload_status(self, status):
        self._FILE_UPLOAD_STATUS = status
