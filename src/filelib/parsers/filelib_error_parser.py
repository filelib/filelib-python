"""
Filelib API returns Content-Type= application/json

Response structure as follows:
    {
        "status": bool,
        "error": str|null,
        "error_code": str|null,
        "data": {}|[]|null
    }

"""
from filelib.utils import parse_api_err

from .base import BaseErrorFormatter


class FilelibErrorParser(BaseErrorFormatter):

    def format(self):
        return parse_api_err(self.response)
