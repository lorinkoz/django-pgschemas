from io import StringIO

from django.core import management
from django.test import TestCase
from django.urls.exceptions import NoReverseMatch


class ExternalURLResolutionTestCase(TestCase):
    """
    Tests whether URLs are properly resolved when outside the request/response cycle.
    In this case, we use a special management command designed to try and reverse a given URL
    in a given schema.
    """

    def test_urls_for_main_error(self):
        with self.assertRaises(NoReverseMatch):
            management.call_command("reverse_url", "entries", schemas=["www"])

    def test_urls_for_main_success(self):
        with StringIO() as buffer:
            management.call_command("reverse_url", "register", schemas=["www"], stdout=buffer)
            buffer.seek(0)
            self.assertEqual(buffer.read().strip(), "/register/")

    def test_urls_for_blog_error(self):
        with self.assertRaises(NoReverseMatch):
            management.call_command("reverse_url", "register", schemas=["blog"])

    def test_urls_for_blog_success(self):
        with StringIO() as buffer:
            management.call_command("reverse_url", "entries", schemas=["blog"], stdout=buffer)
            buffer.seek(0)
            self.assertEqual(buffer.read().strip(), "/entries/")
