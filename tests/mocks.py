from concurrent.futures import Executor, Future
from threading import Lock


class DummyExecutor(Executor):
    """
    Needed this to mock multiprocessing functions in unittests
    Thanks to REF: https://stackoverflow.com/a/10436851
    """

    def __init__(self):
        self._shutdown = False
        self._shutdownLock = Lock()

    def submit(self, fn, *args, **kwargs):
        with self._shutdownLock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f = Future()
            try:
                result = fn(*args, **kwargs)
            except BaseException as e:
                f.set_exception(e)
            else:
                f.set_result(result)

            return f

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    def shutdown(self, *args, **kwargs):
        with self._shutdownLock:
            self._shutdown = True
