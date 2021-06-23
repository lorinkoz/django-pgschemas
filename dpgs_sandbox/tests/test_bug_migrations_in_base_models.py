import warnings
from unittest.mock import patch

from django.core import management
from django.core.management.base import CommandError
from django.db import models
from django.db.utils import ProgrammingError
from django.test import TestCase, tag

from django_pgschemas.models import TenantMixin
from django_pgschemas.utils import get_tenant_model

TenantModel = get_tenant_model()


def patched_get_tenant_model(*args, **kwargs):
    class TenantModel(TenantMixin):
        dummy = models.TextField()

        class Meta:
            app_label = get_tenant_model()._meta.app_label

    return TenantModel


@tag("bug")
class UnappliedMigrationTestCase(TestCase):
    """
    Provoke a handled ProgrammingError by running tenant command with pending model changes.
    """

    @classmethod
    def setUpTestData(cls):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant1.save(verbosity=0)

    @patch("django_pgschemas.management.commands.get_tenant_model", patched_get_tenant_model)
    def test_whowill_with_pending_migrations(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Avoid warnings about model being registered twice
            with self.assertRaises(CommandError) as ctx:
                management.call_command("whowill", all_schemas=True, verbosity=0)
            self.assertEqual(
                str(ctx.exception),
                "Error while attempting to retrieve dynamic schemas. "
                "Perhaps you need to migrate the 'public' schema first?",
            )


@tag("bug")
class MigrateIgnoringExcludedSchemasTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant1.save(verbosity=0)

    def test_migrate_with_exclusions(self):
        # We first unapply a migration with fake so we can reapply it without fake
        # This should work without errors
        management.call_command("migrate", "app_tenants", "0001_initial", fake=True, schemas=["tenant1"], verbosity=0)
        # We then migrate on all schemas except for tenant1, THIS IS THE CASE WE WANT TO TEST
        # This should work without errors
        management.call_command("migrate", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0)
        # If we try to global migrate now, we should get a ProgrammingError
        with self.assertRaises(ProgrammingError):
            management.call_command("migrate", all_schemas=True, verbosity=0)
        # We finally apply the migration again with fake
        # This should work without errors
        management.call_command("migrate", fake=True, all_schemas=True, verbosity=0)
