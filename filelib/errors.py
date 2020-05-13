"""

ERROR MESSAGES DEFINED AS CONSTANTS
"""
from .utils import MINIMUM_CHUNK_SIZE, MAXIMUM_CHUNK_SIZE


NO_FILES_TO_UPLOAD = "No files to upload"
FILE_DOES_NOT_EXIST = "No such file or directory: '{}'"
FILES_PARAMETER_UNSUPPORTED_TYPE = "Files parameter must be a file-like-object or a path as a string"
PATH_MUST_STRING = "Path to file must be type of string."
FILE_UPLOAD_FAILED_DEFAULT_ERROR = "File upload failed and we can't provide an error message at this time."
MINIMUM_CHUNK_SIZE_ERROR = "chunk_size must not be smaller than %d" % MINIMUM_CHUNK_SIZE
MAXIMUM_CHUNK_SIZE_ERROR = "chunk_size must not be bigger than %d" % MAXIMUM_CHUNK_SIZE
CHUNK_SIZE_MUST_BE_TYPE_INT = "chunk_size value must be an integer."
FILE_SIZE_ZERO_ERROR = 'File size is zero'
