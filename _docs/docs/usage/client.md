# Filelib Client

After the going through the installation process, you can start using the components within the library.

Please ensure you acquired your API Credentials for [Authentication](/getting_started/authentication/)

## Client

### Importing `Client` into scope:

```python
from filelib import Client

```


Client object will automatically try to authenticate for you.  
There are 3 ways you can authenticate



!!! note "Supported ways to provide **Authentication Credentials**"

    === "Configuration File"
        
        Reading from a configuration file is the default when initializing `Client`
        The following `credentials_source`, and `credentials_path` are the default values.
        If you have your file at a different path, just update the `credentials_path` value to your path.

        A sample `~/.filelib/credentials` file looks like this:
        ```text
        [filelib]
        api_key=filelib-uuid-api-key
        api_secret=filelib-uuid-api-secret
        ```
        
        Now you can initialize your `Client` as such: 

        ``` python
        from filelib import Client
        
        client = Client(
                source="storage_ref",  # storage configuration reference name.
                prefix="my_dir/"  # This will be added to the beginning of your file name during storage
                access="private"  # Depending what service you are using to store your files, you can set the visibility.
                credentials_source="file", 
                credentials_path="~/.filelib/credentials"  # path the your configuration file
        )
        ```
        
        

    === "Environment Variable"
        
        If you prefer utilizing environment variables, you can set your values in your env with the following keys:
        
        ```bash
        export FILELIB_API_KEY=api_key_value
        ```

        ```bash
        export FILELIB_API_SECRET=api_secret_value
        ```
        
        Now you can initate your `Client` as follows:
        
        ``` python
        from filelib import Client
        
        client = Client(
                source="storage_ref",  # storage configuration reference name.
                prefix="my_dir/"  # This will be added to the beginning of your file name during storage
                access="private"  # Depending what service you are using to store your files, you can set the visibility.
                credentials_source="env"
        )
        ```

## Adding files for upload

After you initialize `Client`, now you can add files to be uploaded by chunks.

=== "Minimal"

    ```python
    from filelib import Client
    
    
    client = Client(storage="storage_ref")
    # Open file
    file = open("~/Downloads/birthday.mp4", "rb")
    client.add_file(file)  # this will add file to be uploaded but will not read it.
    
    ```

=== "Full"
    
    You can provide additional customizations for each file on how you want to handle it.    

    ```python
    from filelib import Client, FilelibConfig
    
    
    client = Client(storage="storage_ref")
    # Open file
    file = open("~/Downloads/birthday.mp4", "rb")
    config = FilelibConfig(storage="storage_ref", prefix="file_prefix", access="file_access")
    client.add_file(
        file=file,
        config=config  # You can pass indivual config object per each file customizing it.
        workers = 4  # This will enable threading while chunks are being uploaded incresing speed.
        ignore_cache=False  # This will turn off caching of file upload progress. Defaults to False.
    )
    ```
    
    !!! warning "Warning"

        Please note that if you decide to set `ignore_cache` to `True`, 
        the upload will not be able to resume from where it left off if it does not complete successfully.
    