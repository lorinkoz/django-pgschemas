from django.test import TestCase

from django_pgschemas.utils import get_tenant_model

TenantModel = get_tenant_model()


class DatabaseCreationTestCase(TestCase):
    def test_tenants_one(self):
        self.assertEqual(TenantModel.objects.count(), 1)
        self.assertEqual(TenantModel.objects.filter(schema_name="dynamic").count(), 1)


class DatabaseOperationsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        class_tenant = TenantModel(schema_name="tenant1")
        class_tenant.save(verbosity=0)

    def setUp(self):
        test_tenant = TenantModel(schema_name="tenant2")
        test_tenant.save(verbosity=0)

    def test_tenants_one(self):
        schema_names = {"dynamic", "tenant1", "tenant2"}
        self.assertEqual(schema_names, set(TenantModel.objects.values_list("schema_name", flat=True)))

    def test_tenants_two(self):
        schema_names = {"dynamic", "tenant1", "tenant2"}
        self.assertEqual(schema_names, set(TenantModel.objects.values_list("schema_name", flat=True)))
