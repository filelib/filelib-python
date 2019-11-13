# filelib-python
Offical python pip package for Filelib API

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
- [x] Implement Upload from file/path method.
- [x] Separate authentication into its own scope. Inject into `Client`
- [x] Remove duplicate upload process handlers from Client.
- [ ] Add config option references.


### Library Authenticator  
Authentication handling will be done in its own scope, separate class that manages authentication processes.


### Upload process within Client

Upload process needs to be as readable and lesser lines as possible.
```python
from filelib import Client

client = Client()
file = 'path_to_local_file'

# TODO: add reference to config options
configs = {}

upload = client.upload(file=file, config=configs)

# Or as the following for file-like object uploads 
# with open('path_to_file', 'rb') as f:
#    upload = client.upload(file=f, config=configs)
```

`Client.upload(file, config)`  
this method accepts two parameters  
1. `file`:  
   `file: type in {str|io.IOBase}`  
   `file` parameter can be of 2 types  
   1. it can be a string which is a path of a local file to be uploaded.  
   2. it can be a file-like object which is equivalent to `open('file', mode='rb')`  
2. `config`:
    `config: type dict| None`  
    `config` parameter can be of 2 types  
    1. It can be `None` is all default config options to be used.  
    2. It can be a dictionery that container config value options at Consumers discretion.    
        ```python
        config = {
           'prefix': 'mysubpath'
        }
        ```

       
       
 
