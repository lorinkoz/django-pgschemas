from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase

from django_pgschemas import utils


class SchemaCreationCommandsTestCase(TransactionTestCase):
    """
    Tests that the schema creation commands do what they are expected to do.
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

    def test_createrefschema(self):
        "Tests 'createrefschema' command"
        utils.drop_schema("cloned")
        call_command("createrefschema", verbosity=0)  # All good
        self.assertTrue(utils.schema_exists("sample"))
        utils.drop_schema("cloned")
        call_command("createrefschema", recreate=True, verbosity=0)  # All good too
        self.assertTrue(utils.schema_exists("sample"))
        utils.drop_schema("cloned")
        call_command("createrefschema", recreate=True, verbosity=0)  # All good too
        self.assertTrue(utils.schema_exists("sample"))


class InteractiveCloneSchemaTestCase(TransactionTestCase):
    """
    Tests the interactive behaviod of the cloneschema command.
    """

    @classmethod
    def setUpClass(cls):
        TenantModel = utils.get_tenant_model()
        DomainModel = utils.get_domain_model()
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.test.com", is_primary=True)

    @classmethod
    def tearDownClass(cls):
        TenantModel = utils.get_tenant_model()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_interactive_cloneschema(self):
        answer_provider = (
            n
            for n in [
                "y",  # Would you like to create a database entry?
                "",  # Domain name, simulated wrong answer
                "tenant2.test.com",  # Domain name, good answer
            ]
        )

        def patched_input(*args, **kwargs):
            return next(answer_provider)

        with patch("builtins.input", patched_input):
            with StringIO() as stdout:
                with StringIO() as stderr:
                    call_command("cloneschema", "tenant1", "tenant2", verbosity=1, stdout=stdout, stderr=stderr)
        self.assertTrue(utils.schema_exists("tenant2"))
