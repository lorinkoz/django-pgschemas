from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from django_pgschemas import utils


class QuickCommandTestCase(TestCase):
    """
    Tests quickly that management commands do what they are expected to do.
    """

    def test_cloneschema(self):
        "Tests 'cloneschema' command"

        @utils.run_in_public_schema
        def fixup():
            utils._create_clone_schema_function()

        fixup()
        self.assertFalse(utils.schema_exists("cloned"))
        call_command("cloneschema", "sample", "cloned", verbosity=0)  # All good
        self.assertTrue(utils.schema_exists("cloned"))
        with self.assertRaises(CommandError):  # Existing destination
            call_command("cloneschema", "sample", "cloned", verbosity=0)
        with self.assertRaises(CommandError):  # Not existing source
            call_command("cloneschema", "nonexisting", "newschema", verbosity=0)
        utils.drop_schema("cloned")

    # def test_createrefschema(self):
    #     "Tests 'createrefschema' command"
    #     utils.drop_schema("cloned")
    #     call_command("createrefschema", verbosity=0)  # All good
    #     self.assertTrue(utils.schema_exists("sample"))
    #     call_command("createrefschema", recreate=True, verbosity=0)  # All good too
    #     self.assertTrue(utils.schema_exists("sample"))
