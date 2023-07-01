from unittest.mock import patch

from django.core import management
from django.core.management.base import CommandError
from django.test import TestCase

from django_pgschemas.management.commands import CommandScope
from django_pgschemas.management.commands.whowill import Command as WhoWillCommand
from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class TenantCommandsTestCase(TestCase):
    """
    Tests the functionality of tenant commands.
    """

    @classmethod
    def setUpClass(cls):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant1.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant1, domain="tenant1.localhost", is_primary=True)
        DomainModel.objects.create(
            tenant=tenant1, domain="everyone.localhost", folder="tenant1", is_primary=False
        )
        tenant2 = TenantModel(schema_name="tenant2")
        tenant2.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant2, domain="tenant2.localhost", is_primary=True)
        DomainModel.objects.create(
            tenant=tenant2, domain="everyone.localhost", folder="tenant2", is_primary=False
        )

    @classmethod
    def tearDownClass(cls):
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_no_schema_provided(self):
        command = WhoWillCommand()
        with self.assertRaises(CommandError) as ctx:
            management.call_command(command, interactive=False, verbosity=0)
        self.assertEqual(str(ctx.exception), "No schema provided")

    def test_no_all_schemas_allowed(self):
        command = WhoWillCommand()
        command.allow_wildcards = False
        with self.assertRaises(TypeError):
            management.call_command(command, all_schemas=True, verbosity=0)

    def test_no_static_schemas_allowed(self):
        command = WhoWillCommand()
        command.scope = CommandScope.DYNAMIC
        with self.assertRaises(CommandError) as ctx:
            management.call_command(command, static_schemas=True, verbosity=0)
        self.assertEqual(str(ctx.exception), "Including static schemas is NOT allowed")
        command = WhoWillCommand()
        command.allow_wildcards = False
        with self.assertRaises(TypeError):
            management.call_command(command, static_schemas=True, verbosity=0)

    def test_no_dynamic_schemas_allowed(self):
        command = WhoWillCommand()
        command.scope = CommandScope.STATIC
        with self.assertRaises(CommandError) as ctx:
            management.call_command(command, dynamic_schemas=True, verbosity=0)
        self.assertEqual(str(ctx.exception), "Including dynamic schemas is NOT allowed")
        command = WhoWillCommand()
        command.allow_wildcards = False
        with self.assertRaises(TypeError):
            management.call_command(command, dynamic_schemas=True, verbosity=0)

    def test_no_tenant_like_schemas_allowed(self):
        command = WhoWillCommand()
        command.scope = CommandScope.STATIC
        with self.assertRaises(CommandError) as ctx:
            management.call_command(command, tenant_schemas=True, verbosity=0)
        self.assertEqual(str(ctx.exception), "Including tenant-like schemas is NOT allowed")
        command = WhoWillCommand()
        command.allow_wildcards = False
        with self.assertRaises(TypeError):
            management.call_command(command, tenant_schemas=True, verbosity=0)

    def test_nonexisting_schema(self):
        with self.assertRaises(CommandError) as ctx:
            management.call_command("whowill", schemas=["unknown"], verbosity=0)
        self.assertEqual(str(ctx.exception), "No schema found for 'unknown'")

    def test_ambiguous_schema(self):
        with self.assertRaises(CommandError) as ctx:
            management.call_command("whowill", schemas=["tenant"], verbosity=0)
        self.assertEqual(
            str(ctx.exception),
            "More than one tenant found for schema 'tenant' by domain, please, narrow down the filter",
        )

    def test_specific_schemas(self):
        command = WhoWillCommand()
        command.specific_schemas = ["blog"]
        with self.assertRaises(CommandError) as ctx:
            management.call_command(command, schemas=["www"], verbosity=0)
        self.assertEqual(str(ctx.exception), "This command can only run in ['blog']")

    def test_nonexisting_schema_excluded(self):
        with self.assertRaises(CommandError) as ctx:
            management.call_command(
                "whowill", all_schemas=True, excluded_schemas=["unknown"], verbosity=0
            )
        self.assertEqual(str(ctx.exception), "No schema found for 'unknown' (excluded)")

    def test_ambiguous_schema_excluded(self):
        with self.assertRaises(CommandError) as ctx:
            management.call_command(
                "whowill", all_schemas=True, excluded_schemas=["tenant"], verbosity=0
            )
        self.assertEqual(
            str(ctx.exception),
            "More than one tenant found for schema 'tenant' by domain (excluded), please, narrow down the filter",
        )

    def test_existing_schema_excluded_ok(self):
        management.call_command(
            "whowill", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0
        )

    def test_interactive_ok(self):
        def patched_input(*args, **kwargs):
            return "blog"

        with patch("builtins.input", patched_input):
            management.call_command("whowill", schemas=[], verbosity=0)

    def test_interactive_nonexisting(self):
        def patched_input(*args, **kwargs):
            return "unknown"

        with patch("builtins.input", patched_input):
            with self.assertRaises(CommandError) as ctx:
                management.call_command("whowill", schemas=[], verbosity=0)
            self.assertEqual(str(ctx.exception), "No schema found for 'unknown'")

    def test_mixed_ok(self):
        management.call_command("whowill", all_schemas=True, verbosity=0)
        management.call_command("whowill", static_schemas=True, verbosity=0)
        management.call_command("whowill", dynamic_schemas=True, verbosity=0)
        management.call_command("whowill", tenant_schemas=True, verbosity=0)
        management.call_command("whowill", schemas=["public", "sample"], verbosity=0)
        management.call_command(
            "whowill",
            all_schemas=True,
            static_schemas=True,
            dynamic_schemas=True,
            tenant_schemas=True,
            schemas=["public", "sample"],
            verbosity=0,
        )
        management.call_command(
            "whowill", all_schemas=True, excluded_schemas=["public", "sample"], verbosity=0
        )
        management.call_command("whowill", schemas=["everyone.localhost/tenant1"], verbosity=0)
        management.call_command("whowill", schemas=["tenant1"], verbosity=0)
        management.call_command(
            "whowill",
            all_schemas=True,
            excluded_schemas=["everyone.localhost/tenant1"],
            verbosity=0,
        )
        management.call_command(
            "whowill", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0
        )
