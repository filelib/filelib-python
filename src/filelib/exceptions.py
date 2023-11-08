from filelib.constants import (
    CREDENTIAL_CAPTURE_OPTIONS,
    CREDENTIALS_FILE_SECTION_NAME,
    ENV_API_KEY_IDENTIFIER,
    ENV_API_SECRET_IDENTIFIER
)


class FilelibBaseException(Exception):
    """
    Base Exception to enable customization
    """

    def __init__(self, message=None, code=None, error_code=None):
        self.message = message if message else getattr(self, "message", None)
        self.code = code if code else getattr(self, "code", None)
        self.error_code = error_code if error_code else getattr(self, "error_code", None)
        super().__init__(self.message)


class ConfigPrefixInvalidError(FilelibBaseException):
    """
    Raised when config `prefix` contains invalid characters
    """
    message = "Config prefix can only contain ASCII characters, digits, _, and -"
    code = 400
    error_code = "CONFIG_PREFIX_INVALID_CHARACTER"


class ConfigValidationError(FilelibBaseException):
    """
    Raised when a validation fails for FilelibConfig parameters
    """
    message = "Validation failed for config options."
    code = 400
    error_code = "FILELIB_CONFIG_VALIDATION_FAILED"


class ValidationError(FilelibBaseException):
    """
    Raised when a validation fails for FilelibConfig parameters
    """
    message = "Validation failed"
    code = 400
    error_code = "FILELIB_VALIDATION_FAILED"


class UnsupportedCredentialsSourceError(FilelibBaseException):
    """
    Raised when credentials_source is an unsupported option
    """
    message = "Credential source is invalid. Must be one of: %s" % ", ".join(CREDENTIAL_CAPTURE_OPTIONS)
    code = 400
    error_code = "CREDENTIAL_SOURCE_INVALID"


class MissingCredentialSectionError(FilelibBaseException):
    """
    Raised when credentials file missing Filelib.CREDENTIALS_CONFIG_FILE_SECTION_NAME('filelib')
    """
    message = "Credential file at provided path is missing %s section" % CREDENTIALS_FILE_SECTION_NAME
    code = 400
    error_code = "CREDENTIAL_FILE_MISSING_FILELIB_SECTION"


class CredentialSectionFilelibAPIKeyMissingException(FilelibBaseException):
    """
    Raised when credentials file filelib section missing Filelib.CREDENTIALS_FILELIB_API_KEY_IDENTIFIER('api_key')
    """
    message = "Credentials file `%s` section is missing required key, value" % CREDENTIALS_FILE_SECTION_NAME
    code = 400
    error_code = "CREDENTIAL_FILE_SECTION_MISSING_KEY_VALUE"


class CredentialsFileDoesNotExistError(FilelibBaseException):
    """
    Credentials file does not exist at given path
    """
    message = "Credentials file cannot be found at given path."
    code = 400
    error_code = "CREDENTIAL_FILE_DOES_NOT_EXIST"


class CredEnvKeyValueMissingError(FilelibBaseException):
    """
    Environment Variables do not contain API KEY and SECRET
    """
    message = "Environment variables do not contain %s and %s" % (ENV_API_KEY_IDENTIFIER, ENV_API_SECRET_IDENTIFIER)
    code = 400
    error_code = "ENVIRONMENT_VARIABLE_MISSING_CREDENTIAL_VALUES"


class AcquiringAccessTokenFailedError(FilelibBaseException):
    """
    Raised when request to acquire ACCESS_TOKEN returns error.
    """
    message = "Failed to acquire access token from Filelib API"
    code = 403
    error_code = "ACCESS_TOKEN_ACQUISITION_FAILURE"


class FileUploadFailedException(FilelibBaseException):
    """
    Raised when request to upload files fails.
    """


class FileUnsupportedReadModeException(FilelibBaseException):
    """
    Raised when file-like object cannot be read in binary mode.
    """
