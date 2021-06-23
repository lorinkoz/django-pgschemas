from django.apps import apps

from django_pgschemas.test.cases import DynamicTenantTestCase

Catalog = apps.get_model("shared_public.Catalog")
TenantData = apps.get_model("app_tenants.TenantData")
User = apps.get_model("shared_common.User")


class TestDynamicTenantTestCase(DynamicTenantTestCase):
    """
    Tests the behavior of the DynamicTenantTestCase.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email="admin@localhost", display_name="Admin")
        cls.catalog = Catalog.objects.create()

    def test_random_operation1(self):
        TenantData.objects.create(user=self.user, catalog=self.catalog)
        self.assertEqual(TenantData.objects.count(), 1)
        self.assertEqual(Catalog.objects.count(), 1)  # No data from other test, only from initialization

    def test_random_operation2(self):
        Catalog.objects.create()
        Catalog.objects.create()
        self.assertEqual(Catalog.objects.count(), 3)
        self.assertEqual(TenantData.objects.count(), 0)  # No data from other test

    def test_random_operation3(self):
        Catalog.objects.all().delete()
        self.assertEqual(Catalog.objects.count(), 0)

    def test_random_operation4(self):
        self.assertEqual(Catalog.objects.count(), 1)


class TestDynamicTenantTestCaseCleanup(DynamicTenantTestCase):
    """
    Tests the cleanup behavior of the DynamicTenantTestCase.
    Works in tandem with previous test case - when running in different orders,
    instances created in the other test shouldn't be here.
    """

    def test_clean(self):
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(TenantData.objects.count(), 0)
        self.assertEqual(Catalog.objects.count(), 0)
