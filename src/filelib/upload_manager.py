import concurrent.futures
import math
import os.path
import zlib

import httpx
from jmcache import Cache
from tqdm import tqdm

from . import Authentication
from .config import FilelibConfig
from .constants import (
    FILE_UPLOAD_STATUS_HEADER,
    FILE_UPLOAD_URL,
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
from .exceptions import (
    AccessToFileDeniedError,
    FileDoesNotExistError,
    FilelibAPIException,
    FileNameRequiredError,
    FileNotSeekableError,
    FileObjectNotReadableError
)


class UploadManager:
    MODE = "rb"
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
            ignore_cache=False
    ):
        self.file_name = file_name
        self.file = self._process_file(file)
        self.config = config
        self.auth = auth
        self.multithreading = True
        self.workers = workers
        self.processed = False
        # Allow the user to start over an upload from scratch
        self.ignore_cache = ignore_cache
        self.cache = cache or Cache(namespace=str(self.get_cache_namespace()), path="./subdir")

    def _process_file(self, file):
        """
        Prepare file to be processed by UploadManager
        If file is a string, validate it exists, readable, accessible
        """
        if type(file) is str:
            # Update if user dir: ~
            path = os.path.expanduser(file)
            # expand if relative.
            path = os.path.abspath(path)

            # Check if exists
            if not os.path.isfile(path):
                raise FileDoesNotExistError("File not found at given path: %s as real path: %s" % (file, path))

            if not os.access(path, os.R_OK):
                AccessToFileDeniedError("Filelib/python does not have permission to read file at: %s" % path)
            # all good. Open and assign file.
            file = open(path, self.MODE)

        # If file(-like object), must be readable
        if not (hasattr(file, "readable")) or not file.readable():
            raise FileObjectNotReadableError("Provided file object is not readable.")
        # file object must be seekable
        if hasattr(file, "seekable"):
            if not file.seekable():
                raise FileNotSeekableError

        if not getattr(file, "name", None) and not self.file_name:
            raise FileNameRequiredError("`file` object does not have a name. Provide a `file_name` value.")
        self.file_name = self.file_name or file.name
        return file

    def has_cache(self):
        # `ignore_cache` setting must return false.
        if self.ignore_cache:
            return False
        return self.cache.get(self._CACHE_LOCATION_KEY) is not None

    def get_cache(self, key):
        if self.ignore_cache:
            return False
        return self.cache.get(key)

    def set_cache(self, key, value):
        if self.ignore_cache:
            return False
        self.cache.set(key, value)

    def get_cache_namespace(self):
        """
        Generate checksum of the first 1000 bytes
        """
        return zlib.crc32(self._get_chunk(1, 1000))

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
                self.cache.delete(self._CACHE_LOCATION_KEY)
                return self._initialize_upload(is_retry=True)
            if not req.is_success:
                raise FilelibAPIException(
                    message="Checking file status from Filelib API failed ",
                    code=req.status_code
                )
            headers = req.headers

            upload_status = headers.get(FILE_UPLOAD_STATUS_HEADER)
            if upload_status == UPLOAD_COMPLETED:
                self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED
                return
            if upload_status == UPLOAD_PENDING:
                self._UPLOAD_PART_NUMBER_SET.update(range(1, self.calculate_part_count() + 1))
                self._FILE_UPLOAD_STATUS = UPLOAD_PENDING
                return
            if upload_status == UPLOAD_STARTED:
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
                self._FILE_UPLOAD_URL = file_url

    def _get_create_payload(self):
        return {
            "file_name": self.file_name,
            "file_size": self.get_file_size()
        }

    def _initialize_upload(self, is_retry=False):

        if not is_retry and self.has_cache():
            return self.get_upload_status()
        headers = self.auth.to_headers()
        headers.update(self.config.to_headers())
        with httpx.Client() as client:
            req = client.post(FILE_UPLOAD_URL, data=self._get_create_payload(), headers=headers)
            if not req.is_success:
                error = req.json().get("error", "Failed to initialize uploading %s to Filelib API" % self.file_name)
                error_code = req.json().get("error_code")
                status_code = req.status_code
                raise FilelibAPIException(
                    message=error,
                    code=status_code,
                    error_code=error_code
                )

            response_headers = req.headers
            self.MAX_CHUNK_SIZE = response_headers.get(UPLOAD_MAX_CHUNK_SIZE_HEADER, self.MAX_CHUNK_SIZE)
            self.MIN_CHUNK_SIZE = response_headers.get(UPLOAD_MIN_CHUNK_SIZE_HEADER, self.MIN_CHUNK_SIZE)
            self.UPLOAD_CHUNK_SIZE = int(response_headers.get(UPLOAD_CHUNK_SIZE_HEADER, self.MAX_CHUNK_SIZE))
            self._FILE_UPLOAD_URL = response_headers.get(UPLOAD_LOCATION_HEADER)
            self._UPLOAD_PART_NUMBER_SET = set(range(1, self.calculate_part_count() + 1))
            self.cache.set(self._CACHE_LOCATION_KEY, self._FILE_UPLOAD_URL)

    def _upload_chunk(self, part_number):

        chunk = self._get_chunk(part_number)
        headers = self.auth.to_headers()
        headers[UPLOAD_PART_CHUNK_NUM_HEADER] = str(part_number)
        headers[UPLOAD_CHUNK_SIZE_HEADER] = str(self.UPLOAD_CHUNK_SIZE)
        with httpx.Client() as client:
            req = client.patch(self._FILE_UPLOAD_URL, content=chunk, headers=headers)
            if not req.is_success:
                raise FilelibAPIException(
                    message="Uploading chunk for part %d  of file %s failed" % (part_number, self.file_name),
                    code=req.status_code
                )

    def single_thread_upload(self):
        parts = sorted(list(self._UPLOAD_PART_NUMBER_SET))
        pbar = tqdm(desc=self.file_name, total=len(parts))
        self._FILE_UPLOAD_STATUS = UPLOAD_STARTED
        # for _part_number in self._UPLOAD_PART_NUMBER_SET:
        for _part_number in parts:
            self._upload_chunk(_part_number)
            pbar.update(_part_number)
        pbar.close()
        self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED

    def multithread_upload(self):
        self._FILE_UPLOAD_STATUS = UPLOAD_STARTED

        # Upload the highest part number last(out of multithread) so server can decide to mark file completed.
        part_nums = list(self._UPLOAD_PART_NUMBER_SET)
        if not part_nums:

            print("Nothing to upload.", part_nums)
            return
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
            _pn_chunk = {executor.submit(self._upload_chunk, pn): pn for pn in part_nums}
            for _processed_chunk in concurrent.futures.as_completed(_pn_chunk):
                completed_part_number = _pn_chunk[_processed_chunk]

                print("PROCESSED CHUNK", _pn_chunk[_processed_chunk])
                try:
                    data = _processed_chunk.result()
                except Exception as exc:
                    print('Uploading %d failed with: %s' % (completed_part_number, exc))
                else:
                    print('Successfully uploaded part: %d with result: %s' % (completed_part_number, data))
        self._upload_chunk(last_part_number)
        self._FILE_UPLOAD_STATUS = UPLOAD_COMPLETED

    def upload(self):
        """
        Upload file object to Filelib API
        """
        self._initialize_upload()
        # print("Uploading %d part numbers" % self.calculate_part_count())
        print("UPLOAD SIZE", self.UPLOAD_CHUNK_SIZE)
        # print("PART NUMBERS TO UPLOAD", self._UPLOAD_PART_NUMBER_SET)

        # if self.multithreading:
        #     return self.multithread_upload()
        return self.single_thread_upload()
