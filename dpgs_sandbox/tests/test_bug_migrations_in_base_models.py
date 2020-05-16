import warnings
from unittest.mock import patch

from django.apps import apps
from django.core import management
from django.core.management.base import CommandError
from django.db import models
from django.test import TransactionTestCase, tag

from django_pgschemas.checks import check_schema_names
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
class MigrationZeroRoundTripTestCase(TransactionTestCase):
    """
    Provoke a handled ProgrammingError by migrating models from empty database.
    """

    def test_database_checks_with_zero_migrations(self):
        management.call_command("migrate", "shared_public", "zero", verbosity=0)
        # The goal is that the next line doesn't raise ProgrammingError
        check_schema_names(apps.get_app_config("django_pgschemas"))
        management.call_command("migrate", verbosity=0)


@tag("bug")
class UnappliedMigrationTestCase(TransactionTestCase):
    """
    Provoke a handled ProgrammingError by running tenant command with pending model changes.
    """

    @classmethod
    def setUpClass(cls):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant1.save(verbosity=0)

    @classmethod
    def tearDownClass(cls):
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

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
