import os
import random
import string

from filelib.constants import FILE_OPEN_MODE
from filelib.exceptions import (
    AccessToFileDeniedError,
    FileDoesNotExistError,
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
