import requests
import json
from configparser import ConfigParser
import os
from datetime import datetime
import jwt
import pytz
from .exceptions import *

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
            import traceback
            traceback.print_exc()
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

    def upload(self, files):
        """
        Upload given files to Filelib API

        :param files: a list object that contains paths of files to be uploaded
            files = [
                (FORM_FIELD_FILE_NAME, open('/Users/musti/Downloads/samples/pyfile-1.pdf', 'rb')),
                (FORM_FIELD_FILE_NAME, open('/Users/musti/Downloads/samples/test', 'rb')),
                (FORM_FIELD_FILE_NAME, open('/Users/musti/Downloads/samples/10mb.jpg', 'rb')),
                (FORM_FIELD_FILE_NAME, open('/Users/musti/Downloads/samples/nasa2.jpg', 'rb')),
                (FORM_FIELD_FILE_NAME, open('/Users/musti/Downloads/samples/nasa3.tif', 'rb')),
            ]
        :return:
        """
        headers = {
            'FILELIB_ACCESS_TOKEN': self.get_access_token()
        }
        data = {
            'make_copy': False
        }

        _files = [(FORM_FIELD_FILE_NAME, open(f_path)) for f_path in files]
        req = requests.post(FILE_UPLOAD_URL, headers=headers, files=files, data=data)
        if not req.ok:
            raise FileUploadFailedException
        json_response = json.loads(req.content)
        return json_response

