import typing

import httpx


class Error(typing.Tuple):
    message: str
    code: int  # Equivalent to HTTP Status Code
    error_code: str


class BaseErrorFormatter:

    def __init__(self, response: httpx.Response):
        self.response = response

    def format(self) -> typing.Tuple[str, int, str]:
        raise NotImplementedError
