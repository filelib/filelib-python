import concurrent.futures
import math
import os.path
import zlib

import httpx
from jmstorage import Cache

from . import Authentication
from .config import FilelibConfig
from .constants import (
    ERROR_CODE_HEADER,
    ERROR_MESSAGE_HEADER,
    FILE_UPLOAD_STATUS_HEADER,
    FILE_UPLOAD_URL,
    UPLOAD_CANCELLED,
    UPLOAD_CHUNK_SIZE_HEADER,
    UPLOAD_COMPLETED,
    UPLOAD_LOCATION_HEADER,
    UPLOAD_MAX_CHUNK_SIZE_HEADER,
    UPLOAD_MIN_CHUNK_SIZE_HEADER,
    UPLOAD_MISSING_PART_NUMBERS_HEADER,
    UPLOAD_PART_CHUNK_NUM_HEADER,
    UPLOAD_PART_NUMBER_POSITION_HEADER,
    UPLOAD_PENDING,
    UPLOAD_STARTED
)
from .exceptions import FilelibAPIException, NoChunksToUpload
from .utils import process_file as proc_file


class UploadManager:
    MB = 2 ** 20
    MAX_CHUNK_SIZE = 64 * MB
    MIN_CHUNK_SIZE = 5 * MB

    # This value can be changed if server responds with previous uploads.
    UPLOAD_CHUNK_SIZE = MAX_CHUNK_SIZE

    _FILE_SIZE: int = None
    _FILE_UPLOAD_URL: str = None

    _FILE_UPLOAD_STATUS = UPLOAD_PENDING
    # This represents what part numbers to upload.
    _UPLOAD_PART_NUMBER_SET = set()

    # Key name for storing unique file URL
    _CACHE_LOCATION_KEY = "LOCATION"

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
        print("IS IT MOCK", self.auth.is_access_token)
        print("IS IT TRUE", self.auth.is_access_token())
        self.multithreading = multithreading
        self.workers = workers
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
        return self.cache.get(self._CACHE_LOCATION_KEY) is not None

    def get_cache(self, key):
        return self.cache.get(key)

    def set_cache(self, key, value):
        if self.ignore_cache:
            return False
        self.cache.set(key, value)

    def get_cache_namespace(self):
        """
        Generate checksum of the first 1000 bytes
        """
        return zlib.crc32(self._get_chunk(1, 1000) + bytes(self.file_name, "utf8"))

    def _get_chunk(self, part_number, chunk_size=None):
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

    def get_upload_status(self):
        """
        If we have a reference for the current file being processed
        we can check from the server how much progress has been made.
        """
        file_url = self.get_cache(self._CACHE_LOCATION_KEY)
        if not file_url:
            raise ValueError("No file url to get status")
        with httpx.Client() as client:
            req = client.head(file_url, headers=self.auth.to_headers())
            # IF 404, means that our cache is out of sync
            # Re-initialize upload.
            if req.status_code == 404:
                print("DELETING CACHE")
                self.cache.delete(self._CACHE_LOCATION_KEY)
                return self._initialize_upload(is_retry=True)
            if not req.is_success:
                raise FilelibAPIException(
                    message="Checking file status from Filelib API failed ",
                    code=req.status_code
                )
            self._FILE_UPLOAD_URL = file_url
            self._set_upload_utils("head", req.headers)

    def _set_upload_utils(self, method, headers: dict) -> None:
        """
        Centralize assigning values to properties that are needed while uploading.
        :param method: str : indicates what the request method is
        :param headers: dict  headers: dict of headers values provided from Filelib API
        """

        upload_status = headers.get(FILE_UPLOAD_STATUS_HEADER) or self._FILE_UPLOAD_STATUS
        self._FILE_UPLOAD_STATUS = upload_status

        if upload_status == UPLOAD_COMPLETED:
            self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED

        elif upload_status == UPLOAD_PENDING:
            self._UPLOAD_PART_NUMBER_SET.update(range(1, self.calculate_part_count() + 1))
            self._FILE_UPLOAD_STATUS = UPLOAD_PENDING

        elif upload_status == UPLOAD_STARTED:
            self._FILE_UPLOAD_STATUS = UPLOAD_STARTED
            self.UPLOAD_CHUNK_SIZE = int(headers.get(UPLOAD_CHUNK_SIZE_HEADER) or self.UPLOAD_CHUNK_SIZE)
            missing_part_numbers = headers.get(UPLOAD_MISSING_PART_NUMBERS_HEADER)
            if missing_part_numbers:
                # values seperated by comma: "1,2,3,4,5"
                missing_part_numbers = map(int, missing_part_numbers.split(","))
                self._UPLOAD_PART_NUMBER_SET.update(missing_part_numbers)
            last_part_number_uploaded = headers.get(UPLOAD_PART_NUMBER_POSITION_HEADER)
            if last_part_number_uploaded:
                rest = range(int(last_part_number_uploaded), self.calculate_part_count() + 1)
                self._UPLOAD_PART_NUMBER_SET.update(rest)

        if method.lower() == "post":
            self.MAX_CHUNK_SIZE = int(headers.get(UPLOAD_MAX_CHUNK_SIZE_HEADER) or self.MAX_CHUNK_SIZE)
            self.MIN_CHUNK_SIZE = int(headers.get(UPLOAD_MIN_CHUNK_SIZE_HEADER) or self.MIN_CHUNK_SIZE)
            self.UPLOAD_CHUNK_SIZE = int(headers.get(UPLOAD_CHUNK_SIZE_HEADER, self.MAX_CHUNK_SIZE))
            self._FILE_UPLOAD_URL = headers.get(UPLOAD_LOCATION_HEADER)
            self._UPLOAD_PART_NUMBER_SET = set(range(1, self.calculate_part_count() + 1))
            self.set_cache(self._CACHE_LOCATION_KEY, self._FILE_UPLOAD_URL)

    def _get_create_payload(self):
        return {
            "file_name": self.file_name,
            "file_size": self.get_file_size(),
            "mimetype": self.content_type
        }

    def _initialize_upload(self, is_retry=False):
        print("IS IT", self.auth.is_access_token())
        if not self.ignore_cache and not is_retry and self.has_cache():
            print("Getting from cache ignore_cache", self.ignore_cache)
            print("Getting from cache is_retry", is_retry)
            print("Getting from cache self.has_cache()", self.has_cache())
            return self.get_upload_status()

        headers = self.auth.to_headers()
        headers.update(self.config.to_headers())
        with httpx.Client() as client:
            req = client.post(FILE_UPLOAD_URL, data=self._get_create_payload(), headers=headers)
            print("RESPONSE HEADERS", req.headers)
            if not req.is_success:
                error = req.json().get("error", "Failed to initialize uploading %s to Filelib API" % self.file_name)
                error_code = req.json().get("error_code")
                status_code = req.status_code
                raise FilelibAPIException(
                    message=error,
                    code=status_code,
                    error_code=error_code
                )

            self._set_upload_utils("post", req.headers)

    def upload_chunk(self, part_number):

        chunk = self._get_chunk(part_number)
        headers = self.auth.to_headers()
        headers[UPLOAD_PART_CHUNK_NUM_HEADER] = str(part_number)
        headers[UPLOAD_CHUNK_SIZE_HEADER] = str(self.UPLOAD_CHUNK_SIZE)
        with httpx.Client() as client:
            req = client.patch(self._FILE_UPLOAD_URL, content=chunk, headers=headers)
            if not req.is_success:
                error = req.headers.get(ERROR_MESSAGE_HEADER) or \
                        "Uploading chunk for part %d  of file %s failed" % (part_number, self.file_name)
                error_code = req.headers.get(ERROR_CODE_HEADER) or FilelibAPIException.error_code
                raise FilelibAPIException(
                    message=error,
                    code=req.status_code,
                    error_code=error_code
                )

    def single_thread_upload(self):
        self._FILE_UPLOAD_STATUS = UPLOAD_STARTED
        for _part_number in self._UPLOAD_PART_NUMBER_SET:
            self.upload_chunk(_part_number)
        self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED

    def multithread_upload(self):
        self._FILE_UPLOAD_STATUS = UPLOAD_STARTED

        # Upload the highest part number last(out of multithread) so server can decide to mark file completed.
        part_nums = list(self._UPLOAD_PART_NUMBER_SET)
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
        print("WORKER COUNT", workers)
        print("UPLAODING PARTS", part_nums)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Start the load operations and mark each future with its URL
            _pn_chunk = {executor.submit(self.upload_chunk, pn): pn for pn in part_nums}
            for _processed_chunk in concurrent.futures.as_completed(_pn_chunk):
                completed_part_number = _pn_chunk[_processed_chunk]

                print("PROCESSED CHUNK", _pn_chunk[_processed_chunk])
                try:
                    _processed_chunk.result()
                except Exception as exc:
                    self.error = str(exc)
                    print('Uploading %d failed with: %s' % (completed_part_number, exc))
        self.upload_chunk(last_part_number)
        self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED

    def cleanup(self):
        # so this works when used in a process.
        self.file = None

    def cancel(self):
        """
        Abort the upload and the server will cancel the upload operation
        and will delete all previously uploaded parts.
        """
        with httpx.Client() as client:
            req = client.delete(self._FILE_UPLOAD_URL, headers=self.auth.to_headers())
            if not req.is_success:
                raise FilelibAPIException(
                    message=req.headers.get(ERROR_MESSAGE_HEADER),
                    error_code=req.headers.get(ERROR_CODE_HEADER),
                    code=req.status_code
                )
            self._FILE_UPLOAD_STATUS = UPLOAD_CANCELLED

    def get_error(self):
        return self.error

    def upload(self):
        """
        Upload file object to Filelib API
        """
        self._initialize_upload()
        if not self._UPLOAD_PART_NUMBER_SET:
            raise NoChunksToUpload("File `%s` does not have any parts to upload.", self.file_name)
        print("Uploading %d part numbers" % self.calculate_part_count())
        print("UPLOAD URL", self._FILE_UPLOAD_URL)
        print("UPLOAD SIZE", self.UPLOAD_CHUNK_SIZE)
        print("ACCESS TOKEn", self.auth.get_access_token())
        try:
            if self.multithreading:
                self.multithread_upload()
            self.single_thread_upload()
        except Exception:
            if self.abort_on_fail:
                self.cancel()
        # Clear cache after successful upload is opted in
        if self.clear_cache:
            self.cache.truncate()
