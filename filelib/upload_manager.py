from .errors import (
    FILES_PARAMETER_UNSUPPORTED_TYPE,
    PATH_MUST_STRING,
    FILE_DOES_NOT_EXIST
)
import io
import os


class UploadManager(object):
    """
    UploadManager is to dynamically handle file opening regardless of the type.
    file passed down inside `with` statement can be a string or a file-like-object
    """
    def __init__(self, file):
        """
        file parameter is provided with `with` statement.
        :param file: str -> Path to the file that will be uploaded.
        """
        self._file = file

    def __verify_file_like_object(self):
        file = self._file
        if not isinstance(file, io.IOBase):
            # Try to provide a name if available to help identify specific object.
            raise AssertionError('Object provided is not a file-like object %s' % getattr(file, 'name', ''))

        if not hasattr(file, 'readable'):
            raise AssertionError("File-like object must have a readable method.")

        if not file.readable():
            raise AssertionError("File-like object must be readable.")
        return True

    def __verify_file_path(self):
        """
        Upload file at given path
        :param path: path to file to be uploaded | string
        :param config: configuration options for the upload | dict|None
        :return: self.upload(**)
        """
        # Ensure the path is a string and the path is a valid destination of file.
        path = self._file
        if type(path) is not str:
            raise ValueError(PATH_MUST_STRING)
        if not os.path.isfile(path):
            raise FileNotFoundError(FILE_DOES_NOT_EXIST)
        return True

    def __enter__(self):
        """
        Read file, if parm is string into memory for upload
        Or read the file-like object from memory for upload.
        https://2.python-requests.org/en/master/user/quickstart/#post-a-multipart-encoded-file
        :return: (FORM_FIELD_FILE_NAME, open('path_to_file/pyfile-1.pdf', 'rb')) : tuple
        """
        file = self._file
        if type(file) is str:
            # Ensure given path is valid and holds file.
            self.__verify_file_path()
            out_file = open(file, 'rb')

        elif isinstance(file, io.IOBase):
            self.__verify_file_like_object()
            out_file = self._file
        else:
            raise ValueError(FILES_PARAMETER_UNSUPPORTED_TYPE)
        self.inline_file = out_file
        return out_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inline_file.close()
