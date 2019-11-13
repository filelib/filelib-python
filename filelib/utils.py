"""
Shared utility functions and Constants

"""


# Tell the API endpoint what kind of package is used to make request
REQUEST_CLIENT_SOURCE = 'python_filelib'

# FILELIB API ENDPOINTS
# These values must be configurable for local dev testing
AUTHENTICATION_URL = "http://localhost:9000/auth/"
FILE_UPLOAD_URL = "http://localhost:9000/upload/"


PYTHON_DATETIME_TIMEZONE = 'UTC'
DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# API Key/Secret can be obtained from the given sources
CONFIG_CAPTURE_OPTIONS = [
    'environment_variable',  # Get API Key/Secret from environment variables
    'credentials_file'  # Get API Key/Secret from a credentials file read via ConfigParser
]

# FORM_FIELD_FILE_NAME = 'filelib_file'
FORM_FIELD_FILE_NAME = 'filelib_file'

# THIS IS THE NAME OF THE KEY IN THE HEADER TO HOLD THE ACCESS TOKEN VALUE
FILELIB_ACCESS_TOKEN_HEADER_NAME = 'FILELIB_ACCESS_TOKEN'

# FOLLOWING IS FOR DEVELOPMENT
# TODO: remove these lines
AUTHENTICATION_URL = 'http://api.localhost/auth/'
FILE_UPLOAD_URL = 'http://api.localhost/upload/'
