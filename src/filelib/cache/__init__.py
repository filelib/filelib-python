

class BaseCaseManager:

    def __init__(self, namespace):
        self.namespace = namespace

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError
