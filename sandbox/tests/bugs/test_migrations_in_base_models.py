import warnings
from unittest.mock import patch

import pytest
from django.apps import apps
from django.core import management
from django.core.management.base import CommandError
from django.db import models
from django.db.utils import ProgrammingError

from django_pgschemas.checks import check_schema_names
from django_pgschemas.models import TenantModel as BaseTenantModel
from django_pgschemas.utils import get_tenant_model


def patched_get_tenant_model(*args, **kwargs):
    if RealTenantModel := get_tenant_model():

        class TenantModel(BaseTenantModel):
            dummy = models.TextField()

            class Meta:
                app_label = RealTenantModel._meta.app_label

        return TenantModel

    return None


@pytest.mark.bug
def test_database_checks_with_zero_migrations(transactional_db):
    """
    Provoke a handled ProgrammingError by migrating models from empty database.
    """
    management.call_command("migrate", "shared_public", "zero", verbosity=0)
    # The goal is that the next line doesn't raise ProgrammingError
    check_schema_names(apps.get_app_config("django_pgschemas"))
    management.call_command("migrate", verbosity=0)


@pytest.mark.bug
@patch("django_pgschemas.management.commands.get_tenant_model", patched_get_tenant_model)
def test_whowill_with_pending_migrations(TenantModel, db):
    """
    Provoke a handled ProgrammingError by running tenant command with pending model changes.
    """
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Avoid warnings about model being registered twice

        with pytest.raises(CommandError) as ctx:
            management.call_command("whowill", all_schemas=True, verbosity=0)

        assert str(ctx.value) == (
            "Error while attempting to retrieve dynamic schemas. "
            "Perhaps you need to migrate the 'public' schema first?"
        )


@pytest.mark.bug
def test_migrate_with_exclusions(TenantModel, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    # We first unapply a migration with fake so we can reapply it without fake
    # This should work without errors
    management.call_command(
        "migrate", "app_tenants", "0001_initial", fake=True, schemas=["tenant1"], verbosity=0
    )

    # We then migrate on all schemas except for tenant1, THIS IS THE CASE WE WANT TO TEST
    # This should work without errors
    management.call_command("migrate", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0)

    # If we try to global migrate now, we should get a ProgrammingError
    with pytest.raises(ProgrammingError):
        management.call_command("migrate", all_schemas=True, verbosity=0)
    # We finally apply the migration again with fake
    # This should work without errors

    management.call_command("migrate", fake=True, all_schemas=True, verbosity=0)
