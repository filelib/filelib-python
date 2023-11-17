import concurrent.futures
import multiprocessing
import zlib

from .authentication import Authentication
from .constants import CREDENTIAL_SOURCE_OPTION_FILE
from .upload_manager import UploadManager
from .utils import get_random_string


def process_file_by_index(instance_index, file_index):
    _file_props = Client._ADDED_FILES[instance_index][file_index]
    up = UploadManager(**_file_props)
    up.upload()
    up.cleanup()
    Client.PROCESSED_FILES[instance_index][file_index] = up
    return file_index


class Client:
    """
    Organize Filelib API operations here
    """
    # Files added to Client for processing.
    _ADDED_FILES: {} = {}
    # Processed files by UploadManager
    PROCESSED_FILES: {} = {}

    def __init__(
            self,
            multiprocess=False,
            workers=4,
            credentials_source=CREDENTIAL_SOURCE_OPTION_FILE,
            credentials_path='~/.filelib/credentials'
    ):
        self.auth = Authentication(source=credentials_source, path=credentials_path)
        self.IS_MULTIPROCESS = multiprocess
        self.workers = workers

        # _ADDED_FILES is a static prop. its values will be updated globally
        # class instance_index will allow access per instance allocation.
        self.instance_index = get_random_string(10)
        Client._ADDED_FILES[self.instance_index] = {}
        Client.PROCESSED_FILES[self.instance_index] = {}

    def __del__(self):
        # Clean up after at exit instance.
        print("CLEANING UP")
        del Client._ADDED_FILES[self.instance_index]
        del Client.PROCESSED_FILES[self.instance_index]

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
        self._ADDED_FILES[self.instance_index][f_index] = ({
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
        return Client._ADDED_FILES.get(self.instance_index)

    def get_processed_files(self):
        return self.PROCESSED_FILES[self.instance_index]

    def _gen_index(self, content: str):
        """
        Generate a unique index for file to be mapped for results if error occurs.
        """
        f_index_joined = "{}{}".format(len(self._ADDED_FILES), content)
        instance_files = self._ADDED_FILES.get(self.instance_index, {})
        return f"{len(instance_files)}_{zlib.crc32(bytes(f_index_joined, 'utf8'))}"

    def single_process(self):
        for index, _file_args in self.get_files().items():
            up = UploadManager(**_file_args)
            up.upload()
            self.PROCESSED_FILES[self.instance_index][index] = up

    def multiprocess_upload(self):
        """
        Upload using multiprocess
        """
        print("MOCKED", concurrent.futures.ProcessPoolExecutor)
        # return
        self.auth.acquire_access_token()
        with multiprocessing.Manager() as mng:
            Client.PROCESSED_FILES[self.instance_index] = mng.dict()
            file_index_list = self.get_files().keys()
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
                processed_future = {executor.submit(process_file_by_index, self.instance_index, index): index for index in file_index_list}
                for future in concurrent.futures.as_completed(processed_future):
                    index = processed_future[future]
                    try:
                        print("INDEX", index)
                        result = future.result()
                        print("RESULT", index, result)
                    except Exception:
                        raise
            # TODO: ensure conversion
            Client.PROCESSED_FILES[self.instance_index] = dict(Client.PROCESSED_FILES[self.instance_index])

    def upload(self):
        """
        Initiate the upload for added files.
        """
        # If multi-processes elected, execute via multiprocessing.
        # TODO: write test for this.
        print("UP Upload", UploadManager.upload)

        if self.IS_MULTIPROCESS:
            return self.multiprocess_upload()
        return self.single_process()
