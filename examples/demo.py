from pprint import pformat

from jmstorage import Cache

from filelib import Client, FilelibConfig

try:
    file = open("media/spacewalk.mp4", "rb")
    # file = open("media/test.txt", "rb")
    # file = io.BytesIO(b"I am some file")
    client = Client()
    config = FilelibConfig(storage="s3main", prefix="cache_dir/", access="private")
    client.auth.acquire_access_token()
    cache = Cache(namespace="upload_" + getattr(file, "name", "yolo"), path="./subdir/yolomulti/")
    for i in range(1):
        file_name = "%d-%s" % (i, getattr(file, "name", "me_file"))
        client.add_file(
            file=file,
            config=config,
            multithreading=False,
            cache=cache,
            file_name=file_name,
            content_type="text/plain",
            abort_on_fail=False,
            # ignore_cache=True
            ignore_cache=False
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

    client.upload()
    print("POST UPLOAD FILES", pformat(client.PROCESSED_FILES))

except Exception:
    import traceback
    traceback.print_exc()
