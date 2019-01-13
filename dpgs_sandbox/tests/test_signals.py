from django.test import TestCase

from django_pgschemas.utils import get_tenant_model, schema_exists


class SignalsTestCase(TestCase):
    """
    Tests signals.
    """

    def test_tenant_delete_callback(self):
        TenantModel = get_tenant_model()
        TenantModel.auto_create_schema = False
        TenantModel.auto_drop_schema = True
        tenant = TenantModel(schema_name="tenant1")
        tenant.save()
        tenant.create_schema(sync_schema=False)
        self.assertTrue(schema_exists("tenant1"))
        TenantModel.objects.all().delete()
        self.assertFalse(schema_exists("tenant1"))
