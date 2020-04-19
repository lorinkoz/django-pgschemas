from django_pgschemas.test.cases import TenantTestCase

from app_tenants.models import TenantData
from shared_common.models import User
from shared_public.models import Catalog


class TestTenantTestCase(TenantTestCase):
    """
    Tests the behavior of the TenantTestCase.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email="admin@localhost", display_name="Admin")
        cls.catalog = Catalog.objects.create()

    def test_random_operation1(self):
        data = TenantData.objects.create(user=self.user, catalog=self.catalog)
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
