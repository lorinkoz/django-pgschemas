import unittest

from django.apps import apps
from django.conf import settings

from django_pgschemas.test.cases import DynamicTenantTestCase

Catalog = apps.get_model("shared_public.Catalog")
User = apps.get_model("shared_common.User")
TenantData = apps.get_model("app_tenants.TenantData") if "default" in settings.TENANTS else None


class TestDynamicTenantTestCase(DynamicTenantTestCase):
    """
    Tests the behavior of the DynamicTenantTestCase.
    """

    @classmethod
    def setUpClass(cls):
        if "default" not in settings.TENANTS:
            raise unittest.SkipTest("Dynamic tenants are not being used")
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email="admin@localhost", display_name="Admin")
        cls.catalog = Catalog.objects.create()

    def test_random_operation1(self):
        if TenantData is None:
            self.skipTest("Dynamic tenants are not being used")
        TenantData.objects.create(user=self.user, catalog=self.catalog)
        self.assertEqual(TenantData.objects.count(), 1)

    def test_random_operation2(self):
        Catalog.objects.create()
        Catalog.objects.create()
        self.assertEqual(Catalog.objects.count(), 3)

    def test_random_operation3(self):
        Catalog.objects.all().delete()
        self.assertEqual(Catalog.objects.count(), 0)

    def test_random_operation4(self):
        self.assertEqual(Catalog.objects.count(), 1)
