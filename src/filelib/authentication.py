import os
from configparser import ConfigParser
from datetime import datetime
from uuid import uuid4

import httpx
import jwt
import pytz

from filelib.constants import (
    AUTHENTICATION_URL,
    AUTHORIZATION_HEADER,
    CREDENTIAL_CAPTURE_OPTIONS,
    CREDENTIAL_SOURCE_OPTION_FILE,
    CREDENTIALS_FILE_SECTION_API_KEY,
    CREDENTIALS_FILE_SECTION_API_SECRET,
    CREDENTIALS_FILE_SECTION_NAME,
    ENV_API_KEY_IDENTIFIER,
    ENV_API_SECRET_IDENTIFIER,
    REQUEST_CLIENT_SOURCE
)
from filelib.exceptions import (
    AcquiringAccessTokenFailedError,
    CredentialSectionFilelibAPIKeyMissingException,
    CredentialsFileDoesNotExistError,
    CredEnvKeyValueMissingError,
    MissingCredentialSectionError,
    UnsupportedCredentialsSourceError,
    ValidationError
)


class Authentication:
    """
    Authenticate client using credentials from supported sources.
    """

    # Identifies the section it needs to parse to extract parameters
    # [filelib]
    # api_key=<uuid>
    # api_secret=<uuid>

    __API_KEY = ""
    __API_SECRET = ""
    __ACCESS_TOKEN = ""
    __ACCESS_TOKEN_EXPIRATION = ""

    def __init__(self, source=None, api_key=None, api_secret=None, path=None):
        """
        api_key and api_secret takes precedence.
        """
        if not source and not (api_key and api_secret):
            raise TypeError("Authentication `source` or credentials pair must be provided(`api_key`, `api_secret`)")
        self.source = source
        self.path = path
        if not api_key and not api_secret and source:
            self._parse_credentials()
        else:
            self.__API_KEY = api_key
            self.__API_SECRET = api_secret

    def _parse_credentials(self):
        if self.source not in CREDENTIAL_CAPTURE_OPTIONS:
            raise UnsupportedCredentialsSourceError
        if self.source == CREDENTIAL_SOURCE_OPTION_FILE:
            return self._parse_credentials_from_file()
        # Fall to ENV Variables.
        return self._parse_credentials_from_env()

    def _parse_credentials_from_file(self):

        if self.source == CREDENTIAL_SOURCE_OPTION_FILE and not self.path:
            raise ValidationError("Path to credential file must be provided when source is %s"
                                  % CREDENTIAL_SOURCE_OPTION_FILE)
        if self.path.startswith("~"):
            self.path = os.path.expanduser(self.path)
        self.path = os.path.abspath(self.path)
        if not os.path.isfile(self.path):
            raise CredentialsFileDoesNotExistError("Credential file path does not exist: %s" % self.path)
        # Parse from the file at self.path
        config = ConfigParser()
        config.read(self.path)
        if not config.has_section(CREDENTIALS_FILE_SECTION_NAME):
            raise MissingCredentialSectionError
        if CREDENTIALS_FILE_SECTION_API_KEY not in config[CREDENTIALS_FILE_SECTION_NAME]:
            raise CredentialSectionFilelibAPIKeyMissingException(
                "Credential file %s missing key : %s"
                % (CREDENTIALS_FILE_SECTION_NAME, CREDENTIALS_FILE_SECTION_API_KEY))
        self.__API_KEY = config.get(CREDENTIALS_FILE_SECTION_NAME, CREDENTIALS_FILE_SECTION_API_KEY)
        if CREDENTIALS_FILE_SECTION_API_SECRET not in config[CREDENTIALS_FILE_SECTION_NAME]:
            raise CredentialSectionFilelibAPIKeyMissingException(
                "Credential file %s missing key : %s"
                % (CREDENTIALS_FILE_SECTION_NAME, CREDENTIALS_FILE_SECTION_API_SECRET))

        self.__API_SECRET = config.get(CREDENTIALS_FILE_SECTION_NAME, CREDENTIALS_FILE_SECTION_API_SECRET)

    def _parse_credentials_from_env(self):
        """
        Client can set credentials within env variables
        """
        key = os.environ.get(ENV_API_KEY_IDENTIFIER, None)
        secret = os.environ.get(ENV_API_SECRET_IDENTIFIER, None)
        if not key:
            raise CredEnvKeyValueMissingError(
                "Environment variables %s does not exist or missing value" % ENV_API_KEY_IDENTIFIER
            )
        if not secret:
            raise CredEnvKeyValueMissingError(
                "Environment variables %s does not exist or missing value" % ENV_API_SECRET_IDENTIFIER
            )

        self.__API_KEY = key
        self.__API_SECRET = secret

    def is_access_token(self):
        """
        Check if an ACTIVE Access Token is present
        :return: Boolean True|False
        """
        return not self.is_expired() and bool(self.__ACCESS_TOKEN)

    def is_expired(self):
        if not self.__ACCESS_TOKEN:
            return True
        if not self.__ACCESS_TOKEN_EXPIRATION:
            return True
        return self.__ACCESS_TOKEN_EXPIRATION < datetime.now(tz=pytz.UTC)

    def get_creds(self):
        return self.__API_KEY, self.__API_SECRET, self.__ACCESS_TOKEN

    def get_access_token(self):
        return self.__ACCESS_TOKEN

    def get_expiration(self):
        return self.__ACCESS_TOKEN_EXPIRATION

    def _access_token_payload(self):
        return {
            "api_key": self.__API_KEY,
            "nonce": str(uuid4()),
            'request_client_source': REQUEST_CLIENT_SOURCE
        }

    # Authorization Methods
    def acquire_access_token(self):
        """
        Acquire an ACCESS TOKEN by utilizing JWT(pyJwt)
        make a POST request to AUTHENTICATION_URL to acquire an access_token
        :return: None
        """
        jwt_payload = self._access_token_payload()
        jwt_encoded = jwt.encode(
            payload=jwt_payload,
            key=self.__API_SECRET,
        )
        if hasattr(jwt_encoded, "decode"):

            jwt_encoded = jwt_encoded.decode("utf8")
        headers = {
            'Authorization': "Bearer {}".format(jwt_encoded)
        }
        with httpx.Client() as client:
            req = client.post(AUTHENTICATION_URL, headers=headers)
            response = req.json()
            if not req.is_success:
                raise AcquiringAccessTokenFailedError(message=response['error'])
            self.__ACCESS_TOKEN = response["data"]["access_token"]
            self.__ACCESS_TOKEN_EXPIRATION = datetime.fromisoformat(response["data"]["expiration"])

    def to_headers(self):
        if not self.is_access_token():
            self.acquire_access_token()
        return {
            AUTHORIZATION_HEADER: "Bearer {}".format(self.get_access_token())
        }
