# FILELIB API ENDPOINTS
# These values must be configurable for local dev testing
AUTHENTICATION_URL = "http://api.filelib.local/api/auth/"
FILE_UPLOAD_URL = "http://api.filelib.local/api/upload/"

# Tell the API endpoint what SDK is communicating.
REQUEST_CLIENT_SOURCE = "python_filelib"

PYTHON_DATETIME_TIMEZONE = 'UTC'
DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# Authentication/Credential
CREDENTIAL_SOURCE_OPTION_FILE = 'credentials_file'
CREDENTIAL_SOURCE_OPTION_ENV = 'environment_variable'
CREDENTIAL_CAPTURE_OPTIONS = [
    CREDENTIAL_SOURCE_OPTION_ENV,
    CREDENTIAL_SOURCE_OPTION_FILE

]

CREDENTIALS_FILE_SECTION_NAME = 'filelib'
CREDENTIALS_FILE_SECTION_API_KEY = 'api_key'
CREDENTIALS_FILE_SECTION_API_SECRET = 'api_secret'

ENV_API_KEY_IDENTIFIER = 'FILELIB_API_KEY'
ENV_API_SECRET_IDENTIFIER = 'FILELIB_API_SECRET'

# HEADERS
