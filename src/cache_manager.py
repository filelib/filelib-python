import os
from sys import platform

if platform == "win32":
    import ntpath as os


class CacheManagerBase:
    pass


class FileCacheManager(CacheManagerBase):

    cache_dir: str

    def __init__(self, namespace, cache_dir=os.path.abspath(os.path.curdir)):
        self.namespace = namespace

