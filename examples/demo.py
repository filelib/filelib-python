import io
import multiprocessing
from pprint import pformat

from jmstorage import Cache

from filelib import Client, FilelibConfig

start_method = multiprocessing.get_start_method()

print("MP START METHOD", start_method)

raise Exception
try:
    # auth = Authentication(source="credentials_file", path="./credentials")
    # print(auth.acquire_access_token())
    # print("HAS ACCESS TOKEN", auth.is_access_token())
    # print("HAS ACCESS TOKEN EXPIRED", auth.is_expired())
    # print("ACCESS TOKEN EXPIRATION", auth.get_expiration())
    # print("ACCESS TOKEN EXPIRED", auth.get_access_token())
    # file = open("media/15mb.jpg", "rb")
    # file = open("media/test.txt", "rb")
    file = io.BytesIO(b"I am some file")
    client = Client(multiprocess=True, workers=None)
    client2 = Client()
    config = FilelibConfig(storage="s3main", prefix="cache_dir/", access="private")
    client.auth.acquire_access_token()
    cache = Cache(namespace="upload_" + getattr(file, "name", "yolo"), path="./subdir/yolomulti/")
    print("ACCESS TOKEN", client.auth.get_access_token())
    for i in range(5):
        file_name = "%d-%s" % (i, getattr(file, "name", "me_file"))
        # file_name = file.name
        cache = Cache(namespace="upload_" + file_name, path="./subdir/yolomulti/")
        print("FILE NAME", file_name)
        print("CACHE LOC", cache.engine.storage_location)
        client.add_file(
            file=file,
            config=config,
            multithreading=False,
            cache=cache,
            file_name=file_name,
            content_type="text/plain",
            abort_on_fail=False
        )

    # file = open("media/test.txt", "rb")
    # cache = Cache(namespace="upload_" + getattr(file, "name", "yolo"), path="./subdir/yolo/")
    # client.add_file(
    #     file=file,
    #     file_name=getattr(file, "name", "yolo"),
    #     config=config,
    #     cache=cache,
    #     multithreading=False,
    #     workers=4,
    #     ignore_cache=False
    # )
    print("ADDED FILES", pformat(list(client._ADDED_FILES.values())[0].keys()))
    print("FILES", client.PROCESSED_FILES)
    client.upload()
    print("POST UPLOAD FILES", pformat(client.PROCESSED_FILES))
    # print("SECOND CLIENT FILES", pformat(client2.PROCESSED_FILES))
    # print("POST UPLOAD FILE STATUS", client.PROCESSED_FILES[0]._FILE_UPLOAD_STATUS)

except Exception:
    import traceback

    traceback.print_exc()
