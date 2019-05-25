import requests
import json
from configparser import ConfigParser
import os
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
    __files = []

    def __init__(self, credentials_source='credentials_file', credentials_path='~/.filelib/credentials'):
        assert credentials_source in CONFIG_CAPTURE_OPTIONS, UnsupportedCredentialsSourceException
        if credentials_source == 'credentials_file':
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.realpath(os.path.expanduser(credentials_path))
            self.config_file_absolute_path = credentials_path
            self._set_credentials_from_file()
        if credentials_source == 'environment_variable':
            self._set_credentials_from_env()
        # ACQUIRE_ACCESS_TOKEN
        if not self.is_access_token():
            self.acquire_access_token()

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

        response = requests.post(AUTHENTICATION_URL, headers=headers)
        json_response = json.loads(response.content)
        assert response.ok, AcquiringAccessTokenFailedException(json_response.get('error', None))

        # access_token_expiration = json_response.get('data', {}).get('expiration')
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
        req = requests.post(FILE_UPLOAD_URL, headers=headers, files=files, data=config)
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
        self.__set_pool_config(config)

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
