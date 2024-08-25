import pytest

from django_pgschemas.schema import Schema, activate
from django_pgschemas.signals import schema_activate
from django_pgschemas.utils import schema_exists


def test_schema_activate():
    response = {}
    schema = Schema.create(schema_name="test")

    def receiver(sender, schema, **kwargs):
        response["schema"] = schema

    schema_activate.connect(receiver)
    activate(schema)
    schema_activate.disconnect(receiver)

    assert response == {"schema": schema}


def test_tenant_delete_callback(TenantModel, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    backup_create, backup_drop = TenantModel.auto_create_schema, TenantModel.auto_drop_schema
    TenantModel.auto_create_schema = False
    TenantModel.auto_drop_schema = True

    tenant = TenantModel(schema_name="tenant_signal")
    tenant.save()
    tenant.create_schema(sync_schema=False)

    assert schema_exists("tenant_signal")

    TenantModel.objects.all().delete()

    assert not schema_exists("tenant_signal")

    TenantModel.auto_create_schema, TenantModel.auto_drop_schema = backup_create, backup_drop
