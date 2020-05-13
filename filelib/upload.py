"""
Place uploading file operations to remote API in this file.
This can be injected into filelib.Client
"""
import json
import os
from sys import platform
from uuid import uuid4

import requests

from .errors import *
from .exceptions import *
from .upload_manager import UploadManager
from .utils import (DEFAULT_CHUNK_SIZE, FILE_UPLOAD_URL,
                    FILELIB_ACCESS_TOKEN_HEADER_NAME, FORM_FIELD_FILE_NAME,
                    MAXIMUM_CHUNK_SIZE, MINIMUM_CHUNK_SIZE)

if platform == "win32":
    import ntpath as os


class Upload:
    """
    Submit a provided file to Filelib API either in chunks that can be assigned by the user/client or by a default


    API UPLOAD PROCESS:

    1. Initiate an upload:
        Make a request to API to create a file entry which return a unique url for the file to be uploaded
    2. Upload each chunk
        Slice/Read file in the size of the chunk_size provided and upload it one by one
        Assign a part number to each chunk.
        ** Race condition will not be a problem since each file has its own unique URL
    3. Return uploaded file information from the method.

    """

    __headers = {}

    def __init__(self, file, auth, config, chunk_size=None):
        """
        Initialize the upload process and the parameters needed to process upload request.

        :param file: File-like-object or path to a file
        :param auth: filelib.auth.Authenticator object instance
        :param config: Dictionary containing upload configuration options
        :param chunk_size: Integer indicating the size of each chunk
        """

        self._set_chunk_size(chunk_size)
        self.config = config
        self.auth = auth
        self.__add_file(file)

    def _set_chunk_size(self, chunk_size):
        """
        Assign the chunk_size to be used for slicing the file.
        Ensure chunk_size is an integer and a value that is within the range of decided MAX and MIN value.
        :param chunk_size: the size to be read and uploaded for file in integer
        :return: None
        """

        if not chunk_size:
            chunk_size = DEFAULT_CHUNK_SIZE
        # Ensure chunk_size is an integer
        assert type(chunk_size) is int, CHUNK_SIZE_MUST_BE_TYPE_INT

        # Ensure chunk is is at least as big as the minimum
        if chunk_size < MINIMUM_CHUNK_SIZE:
            raise AssertionError(MINIMUM_CHUNK_SIZE_ERROR)
        # Ensure chunk_size is not bigger than the maximum
        if chunk_size > MAXIMUM_CHUNK_SIZE:
            raise AssertionError(MAXIMUM_CHUNK_SIZE_ERROR)
        # Assign chunk_size
        self.chunk_size = chunk_size

    def _get_headers(self):
        return self.__headers

    def _set_headers(self, key, value):
        self.__headers[key] = value

    def __add_file(self, file):
        self.__file = file

    def __get_file(self):
        """
        Retrieve the file|file-like object to be uploaded
        Name-mangled to prevent consumption of this method outside of the instance.
        :return:
        """

        return self.__file

    def __init_upload(self, config):
        from .utils import FILE_UPLOAD_INIT_URL
        headers = self._get_headers()
        req = requests.post(FILE_UPLOAD_INIT_URL, headers=headers,  data=config)
        json_reponse = json.loads(req.content)
        assert req.ok, "INITIATING FILE UPLOAD FAILED: %s" % json_reponse.get('error', "NOT SURE")
        return json_reponse

    def _get_chunk(self, file, offset=None):
        """
        `file` is a file-like-object:: open('file.[ext]', 'rb')
        Read and yield the data if any
        if offset is provided, read starting from offset
        :param file: file-object return from UploadManager
        :param offset: integer indicator of where to start reading file from
        :return: read binary data from file.
        """
        while True:
            if offset:
                file.seek(offset=offset)
            data = file.read(self.chunk_size)
            if not data:
                break
            yield data

    def __upload_chunk(self, chunk):
        pass

    def _get_part_count(self, file):
        """
        Calculate how many parts of chunk it will produce from the file given the file size and chunk_size

        :param file: open('some-file', {mode})
        :return: integer
        """
        file_size = file.size
        if file_size == 0:
            raise AssertionError(FILE_SIZE_ZERO_ERROR)

        chunk_size = self.chunk_size
        if chunk_size > file_size:
            return 1
        if file_size % chunk_size == 0:
            return file_size / chunk_size
        else:
            return int(file_size / chunk_size) + 1

    def _sanitize_file_name(self, file_name):
        """
        f = open("{file_path}", {mode})
        `f.name` ::> '/home/dir/some_other_dir/file.ext'
        return file.ext
        :param file_name: string
        :return: string :: file_name cleared from directory names
        """
        if "/" in file_name:
            return os.path.basename(file_name)
        return file_name

    def _upload(self):
        """

        :return: Upload file response
        """
        # Set ACCESS_TOKEN request header
        self._set_headers(FILELIB_ACCESS_TOKEN_HEADER_NAME, self.auth.get_access_token())
        self._set_headers("FILELIB_UPLOAD_RESOURCE_LIBRARY", 'filelibjs')
        headers = self._get_headers()
        config = self.config
        file = self.__get_file()
        with UploadManager(file) as file:
            file_name = self._sanitize_file_name(file.name)
            file_size = file.size
            mimetype = file.mimetype
            config['is_chunked'] = True
            # config['storage'] = 'digitalocean_spaces'
            config['file_size'] = file_size
            config['file_name'] = file_name
            config['part_count'] = self._get_part_count(file)
            config['external_identifier'] = uuid4().__str__()
            config['mimetype'] = mimetype

            counter = 1
            init_upload = self.__init_upload(config)

            for chunk in self._get_chunk(file):
                config['part_number'] = counter
                # files = {'file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}
                request_file_object = {FORM_FIELD_FILE_NAME: (file_name, chunk, mimetype)}

                req = requests.post(init_upload.get('data', {}).get('url'), headers=headers, files=request_file_object, data=config)
                json_response = json.loads(req.content)
                if not req.ok:
                    raise FileUploadFailedException(json_response.get('error', FILE_UPLOAD_FAILED_DEFAULT_ERROR))
                counter += 1
        return json_response
