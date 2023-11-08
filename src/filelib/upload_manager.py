import os.path
from random import randint

from .config import FilelibConfig
from .exceptions import (
    AccessToFileDeniedError,
    FileDoesNotExistError,
    FileNameRequiredError,
    FileObjectNotReadableError, FileNotSeekeableError
)


class UploadManager:

    MODE = "rb"
    MB = 1000000
    MAX_CHUNK_SIZE = 64 * MB
    MIN_CHUNK_SIZE = 5 * MB
    # This value can be changed if server responds with previous uploads.
    UPLOAD_CHUNK_SIZE = MAX_CHUNK_SIZE

    def __init__(self, file, config: FilelibConfig, file_name=None, workers: int = 4):
        self.file_name = file_name
        self.file = self._process_file(file)
        self.config = config
        self.workers = workers
        self.processed = False

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
                raise FileNotSeekeableError

        if not getattr(file, "name", None) and not self.file_name:
            raise FileNameRequiredError("`file` object does not have a name. Provide a `file_name` value.")
        self.file_name = self.file_name or file.name
        return file

    def get_upload_status(self):


    def _initialize_upload(self):

        if self.cache:
            return self.get_upload_status()

    def upload(self):
        """
        Upload file object to Filelib API
        """
        self.processed = randint(1111, 9999)
        print("Processsing file:", self.file_name, self.processed)

    def set_parent(self, parent, up):
        parent.files.append(up)
