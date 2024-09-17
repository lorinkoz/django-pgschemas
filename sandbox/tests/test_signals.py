from unittest.mock import MagicMock

import pytest

from django_pgschemas.schema import Schema, activate, deactivate, get_default_schema
from django_pgschemas.signals import schema_activate
from django_pgschemas.utils import schema_exists


def test_schema_activate():
    deactivate()
    schema = Schema.create(schema_name="test")

    receiver = MagicMock()

    schema_activate.connect(receiver)

    activate(schema)

    schema_activate.disconnect(receiver)

    receiver.assert_called_once_with(signal=schema_activate, sender=Schema, schema=schema)


def test_schema_double_activate():
    deactivate()
    schema = Schema.create(schema_name="test")

    receiver = MagicMock()

    schema_activate.connect(receiver)

    activate(schema)
    activate(schema)

    schema_activate.disconnect(receiver)

    receiver.assert_called_once_with(signal=schema_activate, sender=Schema, schema=schema)


def test_schema_deactivate():
    schema = Schema.create(schema_name="test")
    activate(schema)

    receiver = MagicMock()

    schema_activate.connect(receiver)

    deactivate()

    schema_activate.disconnect(receiver)

    receiver.assert_called_once_with(
        signal=schema_activate, sender=Schema, schema=get_default_schema()
    )


def test_schema_override():
    deactivate()
    schema = Schema.create(schema_name="test")

    receiver = MagicMock()

    schema_activate.connect(receiver)

    with schema:
        pass

    schema_activate.disconnect(receiver)

    receiver.assert_called_once_with(signal=schema_activate, sender=Schema, schema=schema)


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
