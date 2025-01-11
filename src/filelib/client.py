import zlib

from .authentication import Authentication
from .constants import CREDENTIAL_SOURCE_OPTION_FILE
from .upload_manager import UploadManager
from .utils import get_random_string


class Client:
    """
    Organize Filelib API operations here
    """
    def __init__(
            self,
            credentials_source=CREDENTIAL_SOURCE_OPTION_FILE,
            credentials_path='~/.filelib/credentials',
    ):
        self.auth = Authentication(source=credentials_source, path=credentials_path)
        self.instance_index = self._gen_instance_index()
        self.ADDED_FILES = {self.instance_index: {}}
        self.PROCESSED_FILES = {self.instance_index: {}}

    def _gen_instance_index(self):
        return get_random_string(10)

    def add_file(
            self,
            file,
            config,
            file_name=None,
            cache=None,
            multithreading=False,
            workers=None,
            ignore_cache=False,
            abort_on_fail=False,
            content_type=None,
            clear_cache=False
    ):

        file_name, file = UploadManager.process_file(file_name, file)
        f_index = self._gen_index(file_name)
        self.ADDED_FILES[self.instance_index][f_index] = ({
            "file_name": file_name,
            "file": file,
            "config": config,
            "cache": cache,
            "auth": self.auth,
            "multithreading": multithreading,
            "workers": workers,
            "content_type": content_type,
            "ignore_cache": ignore_cache,
            "abort_on_fail": abort_on_fail,
            "clear_cache": clear_cache

        })

    def get_files(self):
        return self.ADDED_FILES.get(self.instance_index)

    def get_processed_files(self):
        return self.PROCESSED_FILES[self.instance_index]

    def _gen_index(self, content: str):
        """
        Generate a unique index for file to be mapped for results if error occurs.
        """
        f_index_joined = "{}{}".format(len(self.ADDED_FILES), content)
        instance_files = self.ADDED_FILES.get(self.instance_index, {})
        return f"{len(instance_files)}_{zlib.crc32(bytes(f_index_joined, 'utf8'))}"

    def single_process(self):
        for index, _file_args in self.get_files().items():
            up = UploadManager(**_file_args)
            up.upload()
            self.PROCESSED_FILES[self.instance_index][index] = up

    def _set_instance_index(self, inst_index):
        self.instance_index = inst_index

    def upload(self):
        """
        Initiate the upload for added files.
        """
        return self.single_process()
