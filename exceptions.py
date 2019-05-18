
class FilelibBaseException(Exception):
    """
    Base Exception to enable customization
    """


class UnsupportedCredentialsSourceException(FilelibBaseException):
    """
    Raised when credentials_source is an unsupported option
    """


class MissingCredentialSectionException(FilelibBaseException):
    """
    Raised when credentials file missing Filelib.CREDENTIALS_CONFIG_FILE_SECTION_NAME('filelib')
    """


class CredentialSectionFilelibAPIKeyMissingException(FilelibBaseException):
    """
    Raised when credentials file filelib section missing Filelib.CREDENTIALS_FILELIB_API_KEY_IDENTIFIER('filelib_api_key')
    """


class CredentialSectionFilelibAPISecretMissingException(FilelibBaseException):
    """
    Raised when credentials file filelib section missing Filelib.CREDENTIALS_FILELIB_API_SECRET_IDENTIFIER('filelib_api_secret')
    """


class CredentialsFileDoesNotExistException(FilelibBaseException):
    """
    Credentials file does not exists at given path
    """


class EnvFilelibAPIKeyValueMissingException(FilelibBaseException):
    """
    Environment Variables do not contain Filelib.ENV_FILELIB_API_KEY_IDENTIFIER(FILELIB_API_KEY)
    """


class EnvFilelibAPISecretValueMissingException(FilelibBaseException):
    """
    Environment Variables do not contain Filelib.ENV_FILELIB_API_SECRET_IDENTIFIER(FILELIB_API_SECRET)
    """


class AcquiringAccessTokenFailedException(FilelibBaseException):
    """
    Raised when request to acquire ACCESS_TOKEN returns error.
    """