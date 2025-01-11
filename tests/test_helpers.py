import io
import os.path
from unittest import TestCase

import httpx

from filelib.constants import ERROR_CODE_HEADER, ERROR_MESSAGE_HEADER
from filelib.utils import get_random_string, parse_api_err, process_file


class HelpersTestCase(TestCase):

    def test_process_file_funtion(self):
        """
        utils.process_file function
        return a tuple.
        """

        base_file_name = "file.txt"
        file_path = os.path.join(os.path.curdir, base_file_name)
        file = io.BytesIO(b"i_am_a_file")
        processed_file_name, processed_file = process_file(file_name=file_path, file=file)
        self.assertEqual(processed_file_name, base_file_name)
        self.assertEqual(file, processed_file)

    def test_get_random_string(self):
        """
        get_random_string returns a random string at given length
        """
        self.assertEqual(type(get_random_string(10)), str)
        self.assertEqual(len(get_random_string(10)), 10)
        self.assertNotEqual(get_random_string(10), get_random_string(10))

    def test_parse_api_err(self):
        """
        Takes a httpx.Response instance.
        extracts error details from headers
        Returns a tuple(error: str, code: int, error_code: str)
        """
        error_headers = {
            ERROR_MESSAGE_HEADER: "test_error_message",
            ERROR_CODE_HEADER: "TEST_ERROR_CODE"
        }
        response = httpx.Response(status_code=400, headers=error_headers)
        error, code, error_code = parse_api_err(response)
        self.assertEqual(error, error_headers[ERROR_MESSAGE_HEADER])
        self.assertEqual(code, 400)
        self.assertEqual(error_code, error_headers[ERROR_CODE_HEADER])
