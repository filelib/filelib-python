from .auth import Authenticator
from .upload import Upload


class Client:
    """
    Organize Filelib API operations here

    *** Do not assign API secret directly accessible.
    *** Make the secret assigned in named-mangled property.

    *** Requests to API endpoint for authentication(acquiring access_token) must not be initialized until upload is called
    TODO: server region in endpoints.


    *** Before uploading a file from memory(file-like object)
        1. Ensure given value is a file-like object
            All streams are gonna be a extended by io.IOBase
            i. `import io; isinstance(file_like_object, io.IOBase)`
        2. Ensure the given stream(file-like object) is readable

    *** Allow upload of a single file per scope only.

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

    # TODO: Maybe load defaults from API end-point
    __config = {
        'make_copy': False
    }
    __headers = {}
    # Handle one file at a time
    __file = None

    # Authentication handler
    # Default is None
    auth = None
    uploader = None

    def __init__(self, credentials_source='credentials_file', credentials_path='~/.filelib/credentials', **kwargs):

        # Assign authentication handler and inject into Client
        self.auth = Authenticator(credentials_source=credentials_source, credentials_path=credentials_path)

    def get_creds(self):
        return self.__FILELIB_API_KEY, self.__FILELIB_API_SECRET

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

    def upload(self, file, config=None, chunk_size=None):
        """
        Upload given files to Filelib API

        :param chunk_size: Integer value of bytes indicating how big each chunk will be.
        :param config: a dict that contains configuration options for the upload process
        :param file: a file-like-object or path to a file to upload
        :return:
        """
        # Ensure the client is authenticated
        # If not, authenticate with given parameters
        # ACQUIRE_ACCESS_TOKEN
        if not self.auth.is_access_token():
            self.auth.acquire_access_token()

        # Set config options for the request
        if config:
            self.__set_pool_config(config)
        self.uploader = Upload(file=file, auth=self.auth, config=self.get_config(), chunk_size=chunk_size)
        return self.uploader._upload()
