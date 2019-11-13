import requests
import json
import os
import io
from .exceptions import *
from .errors import *
from sys import platform
from uuid import uuid4
from .auth import Authenticator
from .upload_manager import UploadManager
from .utils import (
    FILE_UPLOAD_URL,
    FILELIB_ACCESS_TOKEN_HEADER_NAME,
    FORM_FIELD_FILE_NAME
)
# debugging
from pprint import pprint, pformat

if platform == "win32":
    import ntpath as os


class Client:
    """
    Organize Filelib API operations here

    *** Do not assign API secret directly accessible.
    *** Make the secret assigned in named-mangled property.

    *** Requests to API endpoint for authentication(acquiring access_token) must not be initialized until upload is called
    TODO: server region in endpoints.


    *** Before uploading a file from memory(file-like object)
        1. Ensure given value is a file-like object
            All streams are gonna be a extended by io.IOBase
            i. `import io; isinstance(file_like_object, io.IOBase)`
        2. Ensure the given stream(file-like object) is readable

    *** Allow upload of a single file per scope only.

    """

    # This property value is to be set by __init__
    # if credentials_source is `credentials_file`
    config_file_absolute_path = None

    # Following properties are private and only to be set/read privately
    # https://www.python.org/dev/peps/pep-0008/#id36 ->ref: __double_leading_underscore
    __FILELIB_API_KEY = None
    __FILELIB_API_SECRET = None
    __ACCESS_TOKEN = None
    __ACCESS_TOKEN_EXPIRATION = None

    # TODO: Maybe load defaults from API end-point
    __config = {
        'make_copy': False
    }
    __headers = {}
    # Handle one file at a time
    __file = None

    # Authentication handler
    # Default is None
    auth = None

    def __init__(self, credentials_source='credentials_file', credentials_path='~/.filelib/credentials', **kwargs):

        # Assign authentication handler and inject into Client
        self.auth = Authenticator(credentials_source=credentials_source, credentials_path=credentials_path)

    def get_creds(self):
        return self.__FILELIB_API_KEY, self.__FILELIB_API_SECRET

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

    def __prep_file_to_upload(self):
        """
        Read file, if parm is string into memory for upload
        Or read the file-like object from memory for upload.
        https://2.python-requests.org/en/master/user/quickstart/#post-a-multipart-encoded-file

        :return: (FORM_FIELD_FILE_NAME, open('path_to_file/pyfile-1.pdf', 'rb')) : tuple

        """
        file = self.__get_file()
        with UploadManager(file) as file:
            file_name = file.name
            content = file.read()
            file_name = os.path.basename(file_name)
            if not file_name:
                file_name = str(uuid4())
            # {'file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}
            request_file_object = [(FORM_FIELD_FILE_NAME, (file_name, content))]
            return request_file_object

    def __upload_file(self):
        """
        This is where file upload actually takes place.
        :return: dict| json response sent from the API end-point
        """

        # Set ACCESS_TOKEN request header
        self._set_headers(FILELIB_ACCESS_TOKEN_HEADER_NAME, self.auth.get_access_token())

        headers = self._get_headers()
        config = self.get_config()
        # files = [(FORM_FIELD_FILE_NAME, open(file, 'rb'))]
        files = self.__prep_file_to_upload()
        req = requests.post(FILE_UPLOAD_URL, headers=headers, files=files, data=config)
        json_response = json.loads(req.content)
        if not req.ok:
            raise FileUploadFailedException(json_response.get('error', FILE_UPLOAD_FAILED_DEFAULT_ERROR))
        return json_response

    def upload(self, file, config=None):
        """
        Upload given files to Filelib API

        :param config: a dict that contains configuration options for the upload process
        :param file: a file-like-object or path to a file to upload
        :return:
        """
        # Ensure the client is authenticated
        # If not, authenticate with given parameters
        # ACQUIRE_ACCESS_TOKEN
        if not self.auth.is_access_token():
            self.auth.acquire_access_token()

        # Set config options for the request
        self.__set_pool_config(config)
        self.__add_file(file)
        return self.__upload_file()
