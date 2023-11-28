"""
<?xml version="1.0" encoding="UTF-8"?>\n
<Error>
    <Code>NoSuchUpload</Code>
    <Message>The specified upload does not exist. The upload ID may be invalid, or the upload may have been aborted or completed.</Message>
    <UploadId>4B6JVR7779xj7bbbbbbb</UploadId>
    <RequestId>V0NT9TYPPPHAPV6F</RequestId>
    <HostId>MwPflnCyGE7DKM8xeRU112zzXDAwznUMvgQnNu4gaFHnFm2QpQKcoJi8ZbGqYs6cE0jzD1cE2Kc=</HostId>
</Error>
"""
import json
from typing import Any, MutableMapping

import xmltojson


def xmlparser(xml) -> MutableMapping[Any, Any]:
    return json.loads(xmltojson.parse(xml))
