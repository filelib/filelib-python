import json
import os
from configparser import ConfigParser
from datetime import datetime
from io import BufferedReader, TextIOWrapper
# debugging
from pprint import pformat, pprint
from sys import platform
from uuid import uuid4

import jwt
import pytz
import requests

from cache_manager import FileCacheManager
from upload_manager import UploadManager

from .errors import *
from .exceptions import *

if platform == "win32":
    import ntpath as os


class Client:
    """
    Organize Filelib API operations here
    """

    files: [UploadManager] = []
    progress_map: dict = {}

    CACHE_BACKEND_OPTIONS = [
        "filesystem",
        "sqlite",
        "redis"
    ]

    _CACHE_HANDLER_MAP = {
        "filesystem": FileCacheManager
    }





    # These properties point what the setting identifiers will be in Environment variables


    # This property value indicates what the section is called in credentials file.


    # TODO: Maybe load defaults from API end-point
    __config = {
        'make_copy': False
    }
    __headers = {}
    __files = []

    def __init__(
            self,
            credentials_source='credentials_file',
            credentials_path='~/.filelib/credentials',
            ):
        assert credentials_source in CONFIG_CAPTURE_OPTIONS, UnsupportedCredentialsSourceException
        if credentials_source == 'credentials_file':
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.realpath(os.path.expanduser(credentials_path))
            self.config_file_absolute_path = credentials_path
            self._set_credentials_from_file()
        if credentials_source == 'environment_variable':
            self._set_credentials_from_env()

        # Check on config options and assign default values if empty
        self.AUTHENTICATION_URL = kwargs.get('authentication_url', AUTHENTICATION_URL)
        self.FILE_UPLOAD_URL = kwargs.get('file_upload_url', FILE_UPLOAD_URL)



    def __set_pool_config(self, config):
        """
        this is to be used internally by the Client class
        :param config:
        :return:
        """
        self.__config.update(config)

    def set_config(self, key, value):
        # TODO: ignore prohibited key, value alterations
        self.__config[key] = value

    def get_config(self):
        return self.__config

    def get_headers(self):
        return self.__headers

    def set_headers(self, key, value):
        self.__headers[key] = value

    def set_files(self, files: list):
        assert type(files) is list, TypeError(FILES_PARAMETER_UNSUPPORTED_TYPE)
        for file in files:
            self.add_file(file)

    def add_file(self, file: str):
        # Ensure type is string
        assert type(file) is str, TypeError(FILES_PARAMETER_UNSUPPORTED_TYPE)
        # Ensure the path|file exists
        if not os.path.isfile(file):
            raise FileNotFoundError(FILE_DOES_NOT_EXIST.format(file))
        self.__files.append(file)

    def get_files(self):
        return self.__files

    def __prep_file_to_upload(self, file):
        """
        Read file, if parm is string into memory for upload
        Or read the file-like object from memory for upload.
        https://2.python-requests.org/en/master/user/quickstart/#post-a-multipart-encoded-file
        :param file: str -> Path to the file that will be uploaded.

        :return:[
                (FORM_FIELD_FILE_NAME, open('path_to_file/pyfile-1.pdf', 'rb')),
                (FORM_FIELD_FILE_NAME, open('path_to_file/test', 'rb')),
                (FORM_FIELD_FILE_NAME, open('path_to_file/10mb.jpg', 'rb')),
                (FORM_FIELD_FILE_NAME, open('path_to_file/nasa2.jpg', 'rb')),
                (FORM_FIELD_FILE_NAME, open('path_to_file/nasa3.tif', 'rb')),
            ]
        """
        if type(file) is str:
            content = open(file, 'rb')
            file_name = content.name
        else:
            content = file.read()
            file_name = file.name
        file_name = os.path.basename(file_name)
        if not file_name:
            file_name = str(uuid4())
        request_file_object = [(FORM_FIELD_FILE_NAME, (file_name, content))]
        return request_file_object

    def __upload_file(self, file):
        # Set ACCESS_TOKEN request header
        self.set_headers(FILELIB_ACCESS_TOKEN_HEADER_NAME, self.get_access_token())

        headers = self.get_headers()
        config = self.get_config()
        # files = [(FORM_FIELD_FILE_NAME, open(file, 'rb'))]
        files = self.__prep_file_to_upload(file)
        req = requests.post(self.FILE_UPLOAD_URL, headers=headers, files=files, data=config)
        json_response = json.loads(req.content)
        if not req.ok:
            raise FileUploadFailedException(json_response['error'])
        return json_response

    def __upload(self):
        """
        Process files queued for uploading.
        Also read one file at a time into memory
        Send(POST|PUT) one file at a time

        :return: Dict(JSON) response
        """
        # files = self.__pre_files_to_upload()
        out = []
        for file in self.get_files():
            out.append(self.__upload_file(file))

        return out

    def upload(self, files, config=None):
        """
        Upload given files to Filelib API

        :param config: a dict that contains configuration options for the upload process
        :param files: a list object of file paths to upload
        :return:
        """
        # Ensure the client is authenticated
        # If not, authenticate with given parameters
        # ACQUIRE_ACCESS_TOKEN
        if not self.is_access_token():
            self.acquire_access_token()

        # Set config options for the request
        self.__set_pool_config(config)
        #
        self.set_files(files)
        return self.__upload()

    def upload_file_objects(self, files, config=None):
        """
        Upload file-like objects.
        This method allows client to upload a file that is already in memory
        :param files: Type list object with file-like object items
        :param config: a dict that contains configuration options for the upload process
        :return: self.__upload()
        """
        for file in files:
            self.__add_file_like_object(file)
        for key, value in config.items():
            self.set_config(key, value)
        return self.__upload()

    def __add_file_like_object(self, fileobj):
        # A file-like object must be readable in `rb`|binary mode|format
        # If file-like object cannot be read in `rb` or converted to binary on the go,
        # Raise error
        assert hasattr(fileobj, 'readable'), "File-like object must have a readable method."
        assert fileobj.readable(), "File-like object must must be readable."
        if type(fileobj) == BufferedReader:
            pass
        elif type(fileobj) == TextIOWrapper:
            if hasattr(fileobj, 'buffer'):
                fileobj = fileobj.buffer
            else:
                raise FileUnsupportedReadModeException
        self.__files.append(fileobj)
