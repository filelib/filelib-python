from filelib import Authentication, Client, FilelibConfig, UploadManager

try:
    auth = Authentication(source="credentials_file", path="./credentials")
    print(auth.acquire_access_token())
    print("HAS ACCESS TOKEN", auth.is_access_token())
    print("HAS ACCESS TOKEN EXPIRED", auth.is_expired())
    print("ACCESS TOKEN EXPIRATION", auth.get_expiration())
    print("ACCESS TOKEN EXPIRED", auth.get_access_token())
    # file = open("test.txt", "rb")
    # client = Client()
    # config = FilelibConfig(storage="s3main", prefix="mydir/", access="private")
    # client.add_file(file)

except Exception as e :
    import traceback
    traceback.print_exc()