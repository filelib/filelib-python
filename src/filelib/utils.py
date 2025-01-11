import os
import random
import string
from multiprocessing import shared_memory

import httpx

from filelib.constants import (
    ERROR_CODE_HEADER,
    ERROR_MESSAGE_HEADER,
    FILE_OPEN_MODE,
    SHARED_MEMORY_NAME,
    SHARED_MEMORY_START
)
from filelib.exceptions import (
    AccessToFileDeniedError,
    FileDoesNotExistError,
    FilelibAPIException,
    FileNameRequiredError,
    FileNotSeekableError,
    FileObjectNotReadableError
)

# Create utility functions/classes here that can be shared


def process_file(file_name, file):
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
        file = open(path, FILE_OPEN_MODE)

    # If file(-like object), must be readable
    if not (hasattr(file, "readable")) or not file.readable():
        raise FileObjectNotReadableError("Provided file object is not readable.")
    # file object must be seekable
    if hasattr(file, "seekable"):
        if not file.seekable():
            raise FileNotSeekableError

    if not file_name and not getattr(file, "name", None):
        raise FileNameRequiredError("`file` object does not have a name. Provide a `file_name` value.")
    file_name = file_name or file.name
    file_name = os.path.basename(file_name)
    return file_name, file


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def parse_api_err(res: httpx.Response) -> tuple:

    error = res.headers.get(ERROR_MESSAGE_HEADER)
    code = res.status_code
    error_code = res.headers.get(ERROR_CODE_HEADER) or FilelibAPIException.error_code
    return error, code, error_code


# Allow multiprocessing module to share memory between each process.
def get_shared_memory(size=10):
    try:
        shared_mem = shared_memory.SharedMemory(create=True, name=SHARED_MEMORY_NAME, size=size)
        is_new = True
        shared_mem.buf[:len(SHARED_MEMORY_START)] = bytearray(SHARED_MEMORY_START, "utf8")
    except FileExistsError:
        shared_mem = shared_memory.SharedMemory(name=SHARED_MEMORY_NAME)
        is_new = False
    return shared_mem, is_new
