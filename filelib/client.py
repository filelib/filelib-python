import requests
import json
from configparser import ConfigParser
import os
import io
from io import BufferedReader, TextIOWrapper
from datetime import datetime
import jwt
import pytz
from .exceptions import *
from .errors import *
from sys import platform
from uuid import uuid4
# debugging
from pprint import pprint, pformat

if platform == "win32":
    import ntpath as os

# FILELIB API ENDPOINTS
# These values must be configurable for local dev testing
AUTHENTICATION_URL = "http://localhost:9000/auth/"
FILE_UPLOAD_URL = "http://localhost:9000/upload/"

# Tell the API endpoint what kind of package is used to make request
REQUEST_CLIENT_SOURCE = 'python_filelib'

PYTHON_DATETIME_TIMEZONE = 'UTC'
DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M:%S%z"
CONFIG_CAPTURE_OPTIONS = [
    'environment_variable',
    'credentials_file'
]

# FORM_FIELD_FILE_NAME = 'filelib_file'
FORM_FIELD_FILE_NAME = 'filelib_file'

# THIS IS THE NAME OF THE KEY IN THE HEADER TO HOLD THE ACCESS TOKEN VALUE
FILELIB_ACCESS_TOKEN_HEADER_NAME = 'FILELIB_ACCESS_TOKEN'


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

    # These properties point what the setting identifiers will be in credentials file.
    CREDENTIALS_FILELIB_API_KEY_IDENTIFIER = 'filelib_api_key'
    CREDENTIALS_FILELIB_API_SECRET_IDENTIFIER = 'filelib_api_secret'

    # These properties point what the setting identifiers will be in Environment variables
    ENV_FILELIB_API_KEY_IDENTIFIER = 'FILELIB_API_KEY'
    ENV_FILELIB_API_SECRET_IDENTIFIER = 'FILELIB_API_SECRET'

    # This property value indicates what the section is called in credentials file.
    CREDENTIALS_CONFIG_FILE_SECTION_NAME = 'filelib'

    # TODO: Maybe load defaults from API end-point
    __config = {
        'make_copy': False
    }
    __headers = {}
    # Handle one file at a time
    __file = None

    def __init__(self, credentials_source='credentials_file', credentials_path='~/.filelib/credentials', **kwargs):
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

    def is_access_token(self):
        """
        Check if an ACTIVE Access Token is present
        :return: Boolean True|False
        """
        # TODO: Verify Expiration
        try:
            assert self.__ACCESS_TOKEN is not None, "NO_ACCESS_TOKEN_PRESENT"
            assert self.__ACCESS_TOKEN_EXPIRATION and datetime.now(
                tz=pytz.UTC) < self.__ACCESS_TOKEN_EXPIRATION, "Expired"
        except AssertionError as e:
            return False
        return True

    def _set_credentials_from_file(self):
        # Read from the given file
        assert os.path.isfile(self.config_file_absolute_path), CredentialsFileDoesNotExistException
        config = ConfigParser()
        config.read(self.config_file_absolute_path)
        assert self.CREDENTIALS_CONFIG_FILE_SECTION_NAME in config, MissingCredentialSectionException
        config_section = config[self.CREDENTIALS_CONFIG_FILE_SECTION_NAME]
        assert self.CREDENTIALS_FILELIB_API_KEY_IDENTIFIER in config_section, CredentialSectionFilelibAPIKeyMissingException
        assert self.CREDENTIALS_FILELIB_API_SECRET_IDENTIFIER in config_section, CredentialSectionFilelibAPISecretMissingException
        self.__FILELIB_API_KEY = config_section.get(self.CREDENTIALS_FILELIB_API_KEY_IDENTIFIER)
        self.__FILELIB_API_SECRET = config_section.get(self.CREDENTIALS_FILELIB_API_SECRET_IDENTIFIER)

    def _set_credentials_from_env(self):
        filelib_api_key = os.environ.get(self.ENV_FILELIB_API_KEY_IDENTIFIER, None)
        filelib_api_secret = os.environ.get(self.ENV_FILELIB_API_SECRET_IDENTIFIER, None)
        assert filelib_api_key, EnvFilelibAPIKeyValueMissingException
        assert filelib_api_secret, EnvFilelibAPISecretValueMissingException
        self.__FILELIB_API_KEY = filelib_api_key
        self.__FILELIB_API_SECRET = filelib_api_secret

    def get_creds(self):
        return self.__FILELIB_API_KEY, self.__FILELIB_API_SECRET, self.__ACCESS_TOKEN

    def get_access_token(self):
        return self.__ACCESS_TOKEN

    # Authorization Methods
    def acquire_access_token(self):
        """
        Acquire an ACCESS TOKEN by utilizing JWT(pyJwt)
        make a POST request to AUTHENTICATION_URL to acquire an access_token
        :return: None
        """

        # Make a pseudo request temporarily to acquire access_token
        jwt_headers = {}

        jwt_payload = {
            "filelib_api_key": self.__FILELIB_API_KEY,
            'request_client_source': REQUEST_CLIENT_SOURCE
        }
        jwt_encoded = jwt.encode(
            payload=jwt_payload,
            key=self.__FILELIB_API_SECRET,
            headers=jwt_headers
        )
        headers = {
            'FILELIB_API_KEY': self.__FILELIB_API_KEY,
            'Authorization': "Bearer {}".format(jwt_encoded.decode('utf-8'))
        }

        response = requests.post(self.AUTHENTICATION_URL, headers=headers)
        json_response = json.loads(response.content)
        assert response.ok, AcquiringAccessTokenFailedException(json_response.get('error', None))

        self.__ACCESS_TOKEN = json_response.get('data', {}).get('access_token')
        access_token_expiration = json_response.get('data', {}).get('expiration')
        access_token_expiration_date = datetime.strptime(access_token_expiration, DATETIME_PRINT_FORMAT)
        self.__ACCESS_TOKEN_EXPIRATION = access_token_expiration_date

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

    def set_file(self, file):
        if type(file) is str:
            pass
        elif isinstance(file, io.IOBase):
            pass
        else:
            raise TypeError(FILES_PARAMETER_UNSUPPORTED_TYPE)
        # Assign file to Client
        self.__add_file(file)

    def __add_file(self, file):
        self.__file = file

    def get_file(self):
        return self.__file

    def __prep_file_to_upload(self, file):
        """
        Read file, if parm is string into memory for upload
        Or read the file-like object from memory for upload.
        https://2.python-requests.org/en/master/user/quickstart/#post-a-multipart-encoded-file
        :param file: str -> Path to the file that will be uploaded.

        :return: (FORM_FIELD_FILE_NAME, open('path_to_file/pyfile-1.pdf', 'rb')) : tuple

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
        # {'file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}
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
        Return the file assigned for upload
        """

        file = self.get_file()
        return self.__upload_file(file)

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
        if not self.is_access_token():
            self.acquire_access_token()

        # Set config options for the request
        self.__set_pool_config(config)
        #
        self.set_file(file)
        return self.__upload()

    def upload_file_object(self, file, config=None):
        """
        Upload file-like objects.
        This method allows client to upload a file that is already in memory
        :param file: Type list object with file-like object items
        :param config: a dict that contains configuration options for the upload process
        :return: self.__upload()
        """

        self.__add_file_like_object(file)
        for key, value in config.items():
            self.set_config(key, value)
        return self.__upload()

    def __add_file_like_object(self, fileobj):
        """
        Ensure the file has passed through validation

        :param fileobj:
        :return:
        """
        # Ensure the file is an instance of io.IOBase

        if not isinstance(fileobj, io.IOBase):
            # Try to provide a name if available to help identify specific object.
            raise AssertionError('Object provided is not a file-like object %s' % getattr(fileobj, 'name', ''))

        if not hasattr(fileobj, 'readable'):
            raise AssertionError("File-like object must have a readable method.")

        if not fileobj.readable():
            raise AssertionError("File-like object must be readable.")
        self.__add_file(fileobj)

    def upload_from_path(self, path, config=None):
        """
        Upload file at given path
        :param path: path to file to be uploaded | string
        :param config: configuration options for the upload | dict|None
        :return: self.upload(**)
        """
        # Ensure the path is a string and the path is a valid destination of file.
        if type(path) is not str:
            raise ValueError(PATH_MUST_STRING)
        if not os.path.isfile(path):
            raise FileNotFoundError(FILE_DOES_NOT_EXIST)
        # TODO: assign config options
        return self.upload(file=path, config=config)
