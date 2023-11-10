import string

from filelib.constants import (
    CONFIG_ACCESS_HEADER,
    CONFIG_PREFIX_HEADER,
    CONFIG_STORAGE_HEADER
)
from filelib.exceptions import ConfigPrefixInvalidError, ConfigValidationError


class FilelibConfig:

    def __init__(self, storage, prefix="", access="private"):
        self.storage = storage
        self.prefix = prefix
        self.access = access
        self.validate_config()

    def validate_config(self):
        self._validate_storage()
        self._validate_prefix()
        self._validate_access()

    def _validate_prefix(self):

        if not self.prefix:
            return True
        allowed_characters = string.ascii_letters + string.digits + "-" + "_" + "/"
        if not set(self.prefix) <= set(allowed_characters):
            raise ConfigPrefixInvalidError
        return True

    def _validate_storage(self):
        if not self.storage:
            raise ConfigValidationError("`storage` for config must be provided.")
        if type(self.storage) is not str:
            raise ConfigValidationError("`storage` for config must be a string.")
        return True

    def _validate_access(self):
        if not self.access:
            return True
        if type(self.access) is not str:
            raise ConfigValidationError("`access` config option must be a string.")
        return True

    def to_headers(self):
        """
        Generate headers from provided values for Filelib API
        """
        return {
            CONFIG_STORAGE_HEADER: self.storage,
            CONFIG_PREFIX_HEADER: self.prefix,
            CONFIG_ACCESS_HEADER: self.access
        }
