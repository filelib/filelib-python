# FILELIB API ENDPOINTS
# These values must be configurable for local dev testing
AUTHENTICATION_URL = "http://api.filelib.local/api/auth/"
FILE_UPLOAD_URL = "http://api.filelib.local/api/upload/"

# Tell the API endpoint what SDK is communicating.
REQUEST_CLIENT_SOURCE = "python_filelib"

PYTHON_DATETIME_TIMEZONE = 'UTC'
DATETIME_PRINT_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# Authentication/Credential
CREDENTIAL_SOURCE_OPTION_FILE = 'file'
CREDENTIAL_SOURCE_OPTION_ENV = 'env'
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

AUTHORIZATION_HEADER = "Authorization"
CONFIG_STORAGE_HEADER = "Filelib-Config-Storage"
CONFIG_PREFIX_HEADER = "Filelib-Config-Prefix"
CONFIG_ACCESS_HEADER = "Filelib-Config-Access"
UPLOAD_MAX_CHUNK_SIZE_HEADER = "Filelib-Upload-Max-Chunk-Size"
UPLOAD_MIN_CHUNK_SIZE_HEADER = "Filelib-Upload-Min-Chunk-Size"
UPLOAD_MISSING_PART_NUMBERS_HEADER = "Filelib-Upload-Missing-Part-Numbers"
UPLOAD_PART_NUMBER_POSITION_HEADER = "Filelib-Upload-Part-Number-Position"
UPLOAD_PART_CHUNK_NUM_HEADER = "Filelib-Upload-Part-Chunk-Number"
UPLOAD_CHUNK_SIZE_HEADER = "Filelib-Upload-Chunk-Size"
UPLOAD_LOCATION_HEADER = "Location"
FILE_UPLOAD_STATUS_HEADER = "Filelib-File-Upload-Status"

# FILE STATUS; Ref: FILE_UPLOAD_STATUS_HEADER
UPLOAD_PENDING = "pending"  # Initialized but no parts are sent
UPLOAD_STARTED = "started"  # Some parts are sent.
UPLOAD_CANCELLED = "cancelled"  # User or server cancelled the upload.
UPLOAD_COMPLETED = "completed"  # All parts are uploaded and transfer completed entirely.
