from filelib import Client, FilelibConfig

try:
    # auth = Authentication(source="credentials_file", path="./credentials")
    # print(auth.acquire_access_token())
    # print("HAS ACCESS TOKEN", auth.is_access_token())
    # print("HAS ACCESS TOKEN EXPIRED", auth.is_expired())
    # print("ACCESS TOKEN EXPIRATION", auth.get_expiration())
    # print("ACCESS TOKEN EXPIRED", auth.get_access_token())
    # file = open("media/15mb.jpg", "rb")
    file = open("media/test.txt", "rb")
    # io_file = io.BytesIO(b"I am some file")
    client = Client(storage="s3main")
    client.auth.acquire_access_token()
    print("ACCESS TOKEN", client.auth.get_access_token())
    config = FilelibConfig(storage="s3main", prefix="cache_dir/", access="private")
    # for i in range(20):
    #     client.add_file(file=file, config=config, file_name="%d - %s" % (i, file.name))

    client.add_file(file=file, config=config, ignore_cache=True)
    client.upload(multiprocess=False)

except Exception:
    import traceback
    traceback.print_exc()
