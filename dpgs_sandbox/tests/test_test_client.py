from django.test import TestCase

from django_pgschemas.test.client import TenantRequestFactory, TenantClient
from django_pgschemas.utils import get_tenant_model, get_domain_model


class TenantRequestFactoryTestCase(TestCase):
    """
    Test the behavior of the TenantRequestFactory.
    """

    @classmethod
    def setUpClass(cls):
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.test.com", is_primary=True)
        cls.request = TenantRequestFactory(tenant)

    @classmethod
    def tearDownClass(cls):
        TenantModel = get_tenant_model()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_get(self):
        request = self.request.get("/not/important/")
        self.assertEqual(request.build_absolute_uri("/whatever/"), "http://tenant1.test.com/whatever/")

    def test_post(self):
        request = self.request.post("/not/important/")
        self.assertEqual(request.build_absolute_uri("/whatever/"), "http://tenant1.test.com/whatever/")

    def test_put(self):
        request = self.request.put("/not/important/")
        self.assertEqual(request.build_absolute_uri("/whatever/"), "http://tenant1.test.com/whatever/")

    def test_patch(self):
        request = self.request.patch("/not/important/")
        self.assertEqual(request.build_absolute_uri("/whatever/"), "http://tenant1.test.com/whatever/")

    def test_delete(self):
        request = self.request.delete("/not/important/")
        self.assertEqual(request.build_absolute_uri("/whatever/"), "http://tenant1.test.com/whatever/")


class TenantClientTestCase(TestCase):
    """
    Test the behavior of the TenantClient.
    """

    @classmethod
    def setUpClass(cls):
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.test.com", is_primary=True)
        cls.tenant_client = TenantClient(tenant)

    @classmethod
    def tearDownClass(cls):
        TenantModel = get_tenant_model()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_get(self):
        response = self.tenant_client.get("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.tenant_client.post("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_put(self):
        response = self.tenant_client.put("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_patch(self):
        response = self.tenant_client.patch("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_delete(self):
        response = self.tenant_client.delete("/profile/")
        self.assertEqual(response.status_code, 200)
