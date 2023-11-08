import io

from filelib import Authentication, Client, FilelibConfig, UploadManager

try:
    # auth = Authentication(source="credentials_file", path="./credentials")
    # print(auth.acquire_access_token())
    # print("HAS ACCESS TOKEN", auth.is_access_token())
    # print("HAS ACCESS TOKEN EXPIRED", auth.is_expired())
    # print("ACCESS TOKEN EXPIRATION", auth.get_expiration())
    # print("ACCESS TOKEN EXPIRED", auth.get_access_token())
    file = open("test.txt", "rb")
    # file = io.BytesIO(b"I am some file")
    client = Client(storage="s3main")
    config = FilelibConfig(storage="s3main", prefix="mydir/", access="private")
    for i in range(20):

        client.add_file(file=file, config=config, file_name="%d - %s" % (i, file.name))

    # client.add_file(file=file, config=config)
    client.upload(multiprocess=True)

except Exception as e :
    import traceback
    traceback.print_exc()
