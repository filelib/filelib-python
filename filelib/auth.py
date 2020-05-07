"""
This file is to handle the authentication of the Client
before it can use API services
This class instance will be injected into `client.Client`

"""

from configparser import ConfigParser
from datetime import datetime
from .errors import *
from .exceptions import *
import json
import jwt
import pytz
import os
import requests
from .utils import (
    REQUEST_CLIENT_SOURCE,
    DATETIME_PRINT_FORMAT,
    AUTHENTICATION_URL,
    CONFIG_CAPTURE_OPTIONS
)


class Authenticator:

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

    def __init__(self, credentials_source='credentials_file', credentials_path='~/.filelib/credentials', **kwargs):
        if credentials_source not in CONFIG_CAPTURE_OPTIONS:
            raise UnsupportedCredentialsSourceException
        if credentials_source == 'credentials_file':
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.realpath(os.path.expanduser(credentials_path))
            self.config_file_absolute_path = credentials_path
            self._set_credentials_from_file()
        if credentials_source == 'environment_variable':
            self._set_credentials_from_env()

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

    def get_access_token(self):
        return self.__ACCESS_TOKEN

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

    # Authorization Methods
    def acquire_access_token(self):
        """
        Acquire an ACCESS TOKEN by utilizing JWT(pyJwt)
        make a POST request to AUTHENTICATION_URL to acquire an access_token
        :return: None
        """

        # Make a pseudo request temporarily to acquire access_token
        jwt_headers = {
          "alg": "HS256",
          "typ": "JWT"
        }

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

        self.__ACCESS_TOKEN = json_response.get('data', {}).get('access_token')
        access_token_expiration = json_response.get('data', {}).get('expiration')
        access_token_expiration_date = datetime.strptime(access_token_expiration, DATETIME_PRINT_FORMAT)
        self.__ACCESS_TOKEN_EXPIRATION = access_token_expiration_date
