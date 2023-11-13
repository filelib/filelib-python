import os
from unittest import TestCase, mock

from filelib import Authentication
from filelib.constants import (
    CREDENTIAL_SOURCE_OPTION_ENV,
    CREDENTIAL_SOURCE_OPTION_FILE,
    ENV_API_KEY_IDENTIFIER,
    ENV_API_SECRET_IDENTIFIER
)
from filelib.exceptions import (
    CredentialSectionFilelibAPIKeyMissingException,
    CredentialsFileDoesNotExistError,
    CredEnvKeyValueMissingError,
    MissingCredentialSectionError,
    UnsupportedCredentialsSourceError,
    ValidationError
)


class AuthenticationTestCase(TestCase):
    cred_file_mock_content_missing_both = """[filelib]"""
    cred_file_mock_content_missing_secret = """[filelib]\napi_key=iamkey"""

    cred_file_mock_content = \
        """
    [filelib]
    api_key=iam_key
    api_secret=iam_secret
    """

    def test_authentication_init(self):
        # No source or key/secret raises error
        with self.assertRaises(TypeError):
            Authentication()

        # No source, secret missing
        with self.assertRaises(TypeError):
            Authentication(api_key="iamkey")

        # No source, key missing
        with self.assertRaises(TypeError):
            Authentication(api_secret="iamsecret")

        # Not supported source option
        with self.assertRaises(UnsupportedCredentialsSourceError):
            Authentication(source="invalid")

    def test_source_is_file(self):
        # source is file and path not provided.
        with self.assertRaises(ValidationError):
            Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE)

        # config file does not exit
        with self.assertRaises(CredentialsFileDoesNotExistError):
            Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE, path="sike/you/thought")

        with mock.patch("os.path.isfile", return_value=True):
            with self.assertRaises(MissingCredentialSectionError):
                Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE, path="faked/path")

            with mock.patch('builtins.open', new=mock.mock_open(read_data=self.cred_file_mock_content_missing_both)):
                with self.assertRaises(CredentialSectionFilelibAPIKeyMissingException):
                    Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE, path="./faked/path")
                    self.assertEqual(1, 2)

            with mock.patch('builtins.open', new=mock.mock_open(read_data=self.cred_file_mock_content_missing_secret)):
                with self.assertRaises(CredentialSectionFilelibAPIKeyMissingException):
                    Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE, path="./faked/path")

            with mock.patch('builtins.open', new=mock.mock_open(read_data=self.cred_file_mock_content)):
                auth = Authentication(source=CREDENTIAL_SOURCE_OPTION_FILE, path="./faked/path")
                key, secret, _ = auth.get_creds()
                self.assertEqual(key, "iam_key")
                self.assertEqual(secret, "iam_secret")

    def test_source_is_env(self):
        """
        Test against reading api key/secret from env variables
        """

        # Fail when no key or secret is in env
        with self.assertRaises(CredEnvKeyValueMissingError):
            Authentication(source=CREDENTIAL_SOURCE_OPTION_ENV)
            # provide key, not secret
        with mock.patch.dict(os.environ, {ENV_API_KEY_IDENTIFIER: "iam_key"}):
            with self.assertRaises(CredEnvKeyValueMissingError):
                Authentication(source=CREDENTIAL_SOURCE_OPTION_ENV)
        # Secret but not key
        with mock.patch.dict(os.environ, {ENV_API_SECRET_IDENTIFIER: "iam_secret"}):
            with self.assertRaises(CredEnvKeyValueMissingError):
                Authentication(source=CREDENTIAL_SOURCE_OPTION_ENV)
        # Happy path
        env_mock_data = {
            ENV_API_KEY_IDENTIFIER: "iam_key",
            ENV_API_SECRET_IDENTIFIER: "iam_secret"
        }
        with mock.patch.dict(os.environ, env_mock_data):
            auth = Authentication(source=CREDENTIAL_SOURCE_OPTION_ENV)
            key, secret, _ = auth.get_creds()
            self.assertEqual(key, "iam_key")
            self.assertEqual(secret, "iam_secret")

    def test_authentication_init_with_creds(self):
        """
        We can initialize Authentication with directly providing key/secret as parameters.
        """
        auth = Authentication(api_key="iam_key", api_secret="iam_secret")
        key, secret, _ = auth.get_creds()
        self.assertEqual(key, "iam_key")
        self.assertEqual(secret, "iam_secret")
