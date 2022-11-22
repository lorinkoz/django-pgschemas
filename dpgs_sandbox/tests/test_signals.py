from django.test import TestCase

from django_pgschemas.schema import Schema, activate
from django_pgschemas.signals import schema_activate
from django_pgschemas.utils import get_tenant_model, schema_exists

TenantModel = get_tenant_model()


class SignalTestCase(TestCase):
    """
    Tests signals.
    """

    def test_schema_activate(self):
        response = {}
        params = {
            "schema_name": "test",
            "domain_url": "localhost",
            "folder": "folder",
        }

        def receiver(sender, schema, **kwargs):
            response["value"] = schema

        schema_activate.connect(receiver)
        activate(Schema.create(**params))
        schema_activate.disconnect(receiver)
        for key, value in params.items():
            self.assertEqual(value, getattr(response["value"], key))


class TenantDeleteCallbackTestCase(TestCase):
    """
    Tests tenant_delete_callback.
    """

    def setUp(self):
        if TenantModel is None:
            self.skipTest("Dynamic tenants are not being used")

    def test_tenant_delete_callback(self):
        backup_create, backup_drop = TenantModel.auto_create_schema, TenantModel.auto_drop_schema
        TenantModel.auto_create_schema = False
        TenantModel.auto_drop_schema = True
        tenant = TenantModel(schema_name="tenant1")
        tenant.save()
        tenant.create_schema(sync_schema=False)
        self.assertTrue(schema_exists("tenant1"))
        TenantModel.objects.all().delete()
        self.assertFalse(schema_exists("tenant1"))
        TenantModel.auto_create_schema, TenantModel.auto_drop_schema = backup_create, backup_drop
