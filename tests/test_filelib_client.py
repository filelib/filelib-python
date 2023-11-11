from unittest import TestCase

from filelib import Client


class FilelibClientTestCase(TestCase):

    def test_init_filelib_client(self):

        with self.assertRaises(Exception):
            Client()
