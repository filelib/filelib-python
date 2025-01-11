import httpx

from filelib.parsers.aws_error_parser import AWSErrorParser
from filelib.parsers.base import BaseErrorFormatter
from filelib.parsers.filelib_error_parser import FilelibErrorParser


def UploadErrorParser(response: httpx.Response, platform: str, code=400,) -> BaseErrorFormatter: # noqa N802
    error_parser_map = {
        "AWS S3": AWSErrorParser,
        "filelib": FilelibErrorParser
    }
    return error_parser_map.get(platform, FilelibErrorParser)(response=response)
