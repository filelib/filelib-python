# filelib-python
Official python package for Filelib API

### Installation

`pip install filelibpy`

This will install the library to your python environment.

This will also create a command that you can use in your terminal via `filelib`

##  Utilizing Filelib Python library

`filelibpy` provides multiple components that allows you to customize your integration.




### Acquiring Access Token
Access_token must be present in the request headers to be allowed to reach API endpoints
Authentication happens via a JWT sent out in the request headers
Customer does not sign/generate the JWT
Client creates this JWT using `PyJWT` package.

`Client` object takes API Key/Secret to generate the JWT payload and signature.  
`Client` can be passed the Key/Value either from a credentials file or from environment variable.  
if credentials file set to use for Key/Value, the default value is:  
    `~/.filelib/credentials`  
this value can be changed at Customer's discretion:  

```python
from filelib import Client
client = Client(credentials_source='credentials_file', credentials_path='path_to_credentials_file')
```
 
Credentials file must be in the following format:
```text
[filelib]
filelib_api_key=561b788b-2aed-47bd-ac89-0b090ff70a75
filelib_api_secret=7cea6848-6eb4-470c-b0d0-f2850c3b670a
```

If Customer would like to use environment variables to pass Key/Value  
Environment Variables must be as follows:
 ```.env
FILELIB_API_KEY={YOUR_API_KEY}
FILELIB_API_SECRET={YOUR_API_SECRET}
```




### TODO: Dev Notes

- [x] Allow to endpoint to be configurable to enable local dev testing
- [x] Do not make any requests until upload is initiated
