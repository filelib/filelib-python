import io
import os
import shutil
from copy import deepcopy
from unittest import TestCase, mock

from jmstorage import Cache

from filelib import Authentication, Client, FilelibConfig, UploadManager
from filelib.constants import (
    CREDENTIAL_SOURCE_OPTION_ENV,
    CREDENTIAL_SOURCE_OPTION_FILE,
    ENV_API_KEY_IDENTIFIER,
    ENV_API_SECRET_IDENTIFIER
)
from filelib.exceptions import FileNameRequiredError


class FilelibClientTestCase(TestCase):
    cred_file_mock_content_missing_both = """[filelib]"""

    cred_file_mock_content = \
        """
    [filelib]
    api_key=iam_key
    api_secret=iam_secret
    """

    def setUp(self):
        self.config = FilelibConfig(storage="test_storage")
        self.client = self.gen_client()
        self.test_path = "./test_tmp"

        self.file = io.BytesIO(b"iamfile2")
        self.file_name = "test_file_2.txt"
        self.cache = Cache(namespace="upload_" + self.file_name, path=self.test_path)

        self.add_file_params = dict(
            file=self.file,
            config=self.config,
            file_name=self.file_name,
            cache=self.cache,
            multithreading=True,
            workers=5,
            ignore_cache=True,
            abort_on_fail=True,
            content_type="text/plain",
            clear_cache=True
        )

    def test_init_filelib_client(self):
        # Initializing with default values must set to file based authentication
        # Cannot group context-managers in 3.8

        with mock.patch("os.path.isfile", return_value=True):
            with mock.patch('builtins.open', new=mock.mock_open(read_data=self.cred_file_mock_content)):
                client = Client(credentials_path="doesnotexist")
                self.assertEqual(type(client.auth), Authentication)
                self.assertEqual(client.auth.source, CREDENTIAL_SOURCE_OPTION_FILE)
        # Passing env variable must initialize Authentication
        env_payload = {
            ENV_API_KEY_IDENTIFIER: "iam_key",
            ENV_API_SECRET_IDENTIFIER: "iam_secret"
        }
        with mock.patch.dict(os.environ, env_payload):
            client = Client(credentials_source=CREDENTIAL_SOURCE_OPTION_ENV)
            self.assertEqual(type(client.auth), Authentication)
            self.assertEqual(client.auth.source, CREDENTIAL_SOURCE_OPTION_ENV)
        # Initializing Client must create an `instance_index` prop with value.
        client = self.gen_client()
        instance_index = getattr(client, "instance_index", "")
        self.assertTrue(len(instance_index) == 10)
        # Client.ADDED_FILES must have a key value assigned, key being instance_index
        self.assertTrue(instance_index in client.ADDED_FILES)
        # Client.PROCESSED_FILES must have a key:value assigned, key being instance_index
        self.assertTrue(instance_index in client.PROCESSED_FILES)

    def test_client_add_file_method(self):
        """
        Test against Client.add_file(...)
        :return:
        """
        client = self.client
        # missing `file` param must error
        with self.assertRaises(TypeError):
            client.add_file()
        file = io.BytesIO(b'I am a file')
        # Missing `config` param must error
        with self.assertRaises(TypeError):
            client.add_file(file=file)

        # Missing file name must fail
        config = self.config
        with self.assertRaises(FileNameRequiredError):
            client.add_file(file=file, config=config)

        file_name = "test_file"
        # Min requirements must add file to Client.ADDED_FILES list.
        client.add_file(file=file, file_name=file_name, config=config)

        # Test the file is added to `ADDED_FILES` property indexed as a dict
        added_file_list = client.get_files()

        self.assertTrue(len(added_file_list) > 0)
        self.assertEqual(type(added_file_list), dict)
        # Each entry must be indexed with values.
        # {"index": {**params-passed}}
        self.assertEqual(len(added_file_list.keys()), 1)
        added_file = list(added_file_list.values())[0]
        # Values must be a dict
        self.assertEqual(type(added_file), dict)
        # values dict must contain the following keys
        expected_key_list = ['file_name', 'file', 'config', 'cache', 'auth', 'multithreading', 'workers',
                             'content_type', 'ignore_cache', 'abort_on_fail', 'clear_cache']
        self.assertEqual(list(added_file.keys()), expected_key_list)

        # Test default values assigned to optional parameters
        # auth must be set
        self.assertEqual(added_file["auth"], client.auth)
        # cache must be none as it is set inside UploadManager if not provided.
        self.assertEqual(added_file["cache"], None)
        # config param must be part of the values
        self.assertEqual(added_file["config"], config)
        # content_type must be none by default
        self.assertEqual(added_file["content_type"], None)
        # file and file_name keys must be equal to file, file_name params passed
        self.assertEqual(added_file["file"], file)
        self.assertEqual(added_file["file_name"], file_name)
        # ignore cache must be false
        self.assertEqual(added_file["ignore_cache"], False)
        # clear_cache must default to False
        self.assertEqual(added_file["clear_cache"], False)
        # Multithreading must be false.
        self.assertEqual(added_file["multithreading"], False)
        # workers must be None
        self.assertEqual(added_file["workers"], None)

        # Providing all parameters to `add_file`
        file = self.file
        file_name = self.file_name

        # Getting index after it gets added will not match.
        f_index = client._gen_index(file_name)
        client.add_file(**self.add_file_params)

        added_file = client.get_files()[f_index]
        # auth must be set
        # cache must be none as it is set inside UploadManager if not provided.
        self.assertEqual(added_file["cache"], self.cache)
        # config param must be part of the values
        self.assertEqual(added_file["config"], self.config)
        # content_type must be none by default
        self.assertEqual(added_file["content_type"], "text/plain")
        # file and file_name keys must be equal to file, file_name params passed
        self.assertEqual(added_file["file"], self.file)
        self.assertEqual(added_file["file_name"], self.file_name)
        # ignore cache must be false
        self.assertEqual(added_file["ignore_cache"], True)
        # clear_cache must default to False
        self.assertEqual(added_file["clear_cache"], True)
        # Multithreading must be false.
        self.assertEqual(added_file["multithreading"], True)
        # workers must be None
        self.assertEqual(added_file["workers"], 5)

    def gen_client(self, *args, **kwargs):
        with mock.patch("os.path.isfile", return_value=True):
            with mock.patch('builtins.open', new=mock.mock_open(read_data=self.cred_file_mock_content)):
                return Client(*args, **kwargs)

    @mock.patch("filelib.client.Client._gen_index")
    def test_add_file_calls_gen_file_index(self, gen_index):
        """
        Client.add_file method must call gen_index method
        """
        client = self.gen_client()
        client.add_file(file=io.BytesIO(b"content"), file_name="test", config=self.config)
        gen_index.assert_called_once()

    def test_single_process_upload_method(self):
        """
        Initializing the Client with multiprocess False must use single process upload.
        Must call `Client.single_process`
        Aftermath must set Client.PROCESSED_FILES[instance_index][file_index] to instance of UploadManager

        """
        client = self.gen_client()
        params = deepcopy(self.add_file_params)
        client.add_file(**params)
        with mock.patch("filelib.UploadManager.upload", return_value=lambda x: None):
            client.upload()
            file_index = list(client.get_files().keys())[0]
            self.assertTrue(file_index in client.get_processed_files())
            processed_file = client.get_processed_files()[file_index]
            self.assertEqual(type(processed_file), UploadManager)

    def tearDown(self):
        # Remove Cache storage path after tests are done.
        shutil.rmtree(self.test_path, ignore_errors=True)
