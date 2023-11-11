import concurrent.futures
import os

from jmcache import Cache as FileCacheManager

from filelib.config import FilelibConfig

from .authentication import Authentication
from .constants import CREDENTIAL_SOURCE_OPTION_FILE
from .upload_manager import UploadManager


# This is to allow access to added files within a multiprocess
class _FileIndexManager:
    files = {}


# global _file_indexes
_file_indexes = _FileIndexManager()


def process_file_by_index(index,):

    _file_indexes.files[index].upload()
    print("Handling index", index, _file_indexes.files[index].processed, os.getpid())
    return index


class Client:
    """
    Organize Filelib API operations here
    """

    files: [UploadManager] = []
    progress_map: dict = {}

    CACHE_BACKEND_OPTIONS = [
        "filesystem",
        "sqlite",
        "redis"
    ]

    _CACHE_HANDLER_MAP = {
        "filesystem": FileCacheManager
    }

    def __init__(
            self,
            storage,
            prefix=None,
            access=None,
            credentials_source=CREDENTIAL_SOURCE_OPTION_FILE,
            credentials_path='~/.filelib/credentials',
            ):

        self.auth = Authentication(source=credentials_source, path=credentials_path)
        self.config = FilelibConfig(storage=storage, prefix=prefix, access=access)

    def add_file(self, file, config=None, file_name=None, workers=4):
        if not config:
            config = self.config
        if not config:
            raise TypeError("`config` must be provided.")
        _file_indexes.files[len(_file_indexes.files)] = (UploadManager(
            file=file,
            auth=self.auth,
            config=config,
            file_name=file_name,
            workers=workers
        ))

    def get_files(self):
        return _file_indexes.files

    def single_process(self):
        for up in _file_indexes.files.values():
            up.upload()
            self.files.append(up)

    def multiprocess_upload(self, workers=None):
        """
        Upload using multiprocess
        """

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            submitted_indexes = {index: executor.submit(process_file_by_index, index) for index in _file_indexes.files.keys()}
            for future in concurrent.futures.as_completed(submitted_indexes.values()):
                try:
                    result_index = future.result()
                    print("RESULT", result_index)
                    up = _file_indexes.files.get(int(result_index))
                    print("_file_indexes.files", up, up.processed)
                    self.files.append(up)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print("Failed with: ", e)

    def upload(self, multiprocess=False, workers=None):
        """
        Initiate the upload for added files.
        """
        # If multi-processes elected, execute via multiprocessing.
        if multiprocess:
            return self.multiprocess_upload(workers)
        return self.single_process()
