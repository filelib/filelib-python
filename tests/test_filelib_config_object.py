from unittest import TestCase

from filelib.config import FilelibConfig
from filelib.exceptions import ConfigPrefixInvalidError, ConfigValidationError


class FilelibConfigTestCase(TestCase):

    def test_storage_config_option(self):
        # Require storage config option.
        with self.assertRaises(TypeError):
            FilelibConfig()
        # Test storage must be a string
        with self.assertRaises(ConfigValidationError):
            FilelibConfig(storage=11)

        # Happy Path
        storage_name = "my_storage"
        config = FilelibConfig(storage=storage_name)
        self.assertEqual(storage_name, config.storage)

    def test_prefix_config_option(self):
        # Test unsupported characters
        with self.assertRaises(ConfigPrefixInvalidError):
            FilelibConfig(storage="my_storage", prefix="invalid******")

        # Test happy path
        prefix_name = "some_prefix/"
        config = FilelibConfig(storage="my_storage", prefix=prefix_name)
        self.assertEqual(prefix_name, config.prefix)

    def test_access_config_option(self):
        # Test must be a string
        with self.assertRaises(ConfigValidationError):
            FilelibConfig(storage="my_storage", access=134234)
