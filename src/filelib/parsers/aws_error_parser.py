"""
Direct uploads to AWS S3 or compatible APIs will return errors in a certain format.
Parse it into a unified structure for standardization.

Sample Error Response Content:

    <?xml version="1.0" encoding="UTF-8"?>
    <Error>
        <Code>NoSuchUpload</Code>
        <Message>The specified upload does not exist. The upload ID may be invalid, or the upload may have been aborted or completed.</Message>
        <UploadId>4B6JVR7779xj7bbbbbbb</UploadId>
        <RequestId>V0NT9TYPPPHAPV6F</RequestId>
        <HostId>MwPflnCyGE7DKM8xeRU112zzXDAwznUMvgQnNu4gaFHnFm2QpQKcoJi8ZbGqYs6cE0jzD1cE2Kc=</HostId>
    </Error>



"""
from .base import BaseErrorFormatter
from .xml import xmlparser


class AWSErrorParser(BaseErrorFormatter):

    def format(self):
        """
        AWS S3 requests return XML
        parse to xml and return Error(NamedTuple)
        """
        response = self.response
        error_xml = response.content
        print("CONTENT TO PARSE", error_xml)
        error = xmlparser(error_xml).get("Error", {})
        code = response.status_code
        error_code = error.get("Code")
        error_msg = error.get("Message")
        return error_msg, code, error_code
