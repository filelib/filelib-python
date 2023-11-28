import json
import os
from concurrent.futures import Executor, Future
from contextlib import contextmanager
from threading import Lock
from unittest import mock

import httpx

from filelib import Authentication
from filelib.constants import (
    CONTENT_TYPE_HEADER,
    CONTENT_TYPE_JSON,
    CREDENTIAL_SOURCE_OPTION_ENV,
    ENV_API_KEY_IDENTIFIER,
    ENV_API_SECRET_IDENTIFIER
)


class DummyExecutor(Executor):
    """
    Needed this to mock multiprocessing functions in unittests
    Thanks to REF: https://stackoverflow.com/a/10436851
    """

    def __init__(self):
        self._shutdown = False
        self._shutdownLock = Lock()

    def submit(self, fn, *args, **kwargs):
        with self._shutdownLock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f = Future()
            try:
                result = fn(*args, **kwargs)
            except BaseException as e:
                f.set_exception(e)
            else:
                f.set_result(result)

            return f

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    def shutdown(self, *args, **kwargs):
        with self._shutdownLock:
            self._shutdown = True


@contextmanager
def auth_patcher(*args, **kwargs):
    env_mock_data = {
        ENV_API_KEY_IDENTIFIER: "iam_key",
        ENV_API_SECRET_IDENTIFIER: "iam_secret"
    }
    with mock.patch.dict(os.environ, env_mock_data):
        with mock.patch("filelib.Authentication.is_access_token", return_value=True):
            yield mock.patch("filelib.Authentication.get_access_token", return_value="iam_access_token")


def mock_authentication(*args, **kwargs):
    with auth_patcher():
        auth = Authentication(source=CREDENTIAL_SOURCE_OPTION_ENV)
    auth = mock.create_autospec(Authentication, instance=auth)
    auth.is_access_token.return_value = True
    auth.get_access_token.return_value = "I_am_access_token"
    return auth


@contextmanager
def mock_request(method, response=None, status_code=200, headers=None):
    trg = "httpx.Client.{method}".format(method=method)
    env_mock_data = {
        ENV_API_KEY_IDENTIFIER: "iam_key",
        ENV_API_SECRET_IDENTIFIER: "iam_secret"
    }

    if not headers:
        headers = {
            CONTENT_TYPE_HEADER: CONTENT_TYPE_JSON
        }

    if CONTENT_TYPE_HEADER not in headers:
        headers[CONTENT_TYPE_HEADER] = CONTENT_TYPE_JSON

    content = {} if not response else response
    if headers[CONTENT_TYPE_HEADER] == CONTENT_TYPE_JSON:

        content = json.dumps(content)

    with mock.patch.dict(os.environ, env_mock_data):
        with mock.patch("filelib.Authentication.is_access_token", return_value=True):
            with mock.patch("filelib.Authentication.get_access_token", return_value="iam_access_token"):
                request = httpx.Request(method=method, url="")
                ret_val = httpx.Response(status_code=status_code, request=request, headers=headers, content=content)
                with mock.patch(trg, return_value=ret_val) as req:
                    yield req


# Mock response for GET 200 /api/upload/<file_id>/
GET_UPLOAD_STATUS_RESPONSE_BODY = {
    "status": True,
    "error": None,
    "error_code": None,
    "data": {
        "is_direct_upload": True,
        "upload_urls": {
            "1": {
                "part_number": 1,
                "url": "https://testservercontainer/some/path",
                "log_url": "http://testserver/file_id/1/log-part-number-upload/",
                "method": "put",
                "platform": "AWS S3"
            }
        }
    }
}
