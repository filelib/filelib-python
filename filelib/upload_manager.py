import io
import os
from magic import Magic

from uuid import uuid4
from .errors import (FILE_DOES_NOT_EXIST, FILES_PARAMETER_UNSUPPORTED_TYPE,
                     PATH_MUST_STRING)


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

    def get_mimetype(self):
        """
        Attempt to get the mimetype of uploaded file
        By default try to retrieve file mimetype from file-like-object as in `content_type` property in case it is a django file.
        If `content_type` property has no value, Ask Magic for help
        :return: mimetype|(string)
        """
        mimetype = None
        file = self._file
        # Cover Django file object in case it is a Django file object
        if hasattr(file, 'content_type'):
            mimetype = getattr(file, 'content_type', None)

        # Call upon the Magic lords since `content_type` has no value
        if not mimetype or mimetype == 'application/octet-stream':
            # NOTE: DO not read the entire file(-like) object
            if type(file) is str:
                file = open(file, 'rb')
            mimetype = Magic(mime=True).from_buffer(file.read(1024))
            # Just in case not reading the entire file did not return a mimetype value
            # read entire file to better determine
            if not mimetype:
                file.open()
                mimetype = Magic(mime=True).from_buffer(file.read())
        return mimetype

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
            self.size = os.path.getsize(file)

        elif isinstance(file, io.IOBase):
            self.__verify_file_like_object()
            out_file = self._file
            out_file.seek(0, os.SEEK_END)
            self.size = out_file.tell()
            out_file.seek(0, os.SEEK_SET)
        else:
            raise ValueError(FILES_PARAMETER_UNSUPPORTED_TYPE)
        self.inline_file = out_file
        self.name = self.__get_file_name(out_file)
        out_file.size = self.size
        if not hasattr(out_file, 'name'):
            out_file.name = self.name
        if not hasattr(out_file, 'mimetype'):
            out_file.mimetype = self.get_mimetype()
        return out_file

    def __get_file_name(self, file):
        file_name = None
        if hasattr(file, 'name'):
            file_name = file.name
        if not file_name:
            if type(self._file) is str():
                file_name = os.path.basename(file_name)
        if not file_name:
            file_name = str(uuid4())
        return file_name

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inline_file.close()
