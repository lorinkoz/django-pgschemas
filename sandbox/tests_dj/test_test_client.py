import unittest

from django.test import TestCase

from django_pgschemas.schema import Schema
from django_pgschemas.test.client import TenantClient, TenantRequestFactory
from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class TenantRequestFactoryTestCase(TestCase):
    """
    Test the behavior of the TenantRequestFactory.
    """

    @classmethod
    def setUpClass(cls):
        if TenantModel is None:
            raise unittest.SkipTest("Dynamic tenants are not being used")
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.localhost", is_primary=True)
        cls.request = TenantRequestFactory(tenant)

    @classmethod
    def tearDownClass(cls):
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_get(self):
        request = self.request.get("/not/important/")
        self.assertEqual(
            request.build_absolute_uri("/whatever/"), "http://tenant1.localhost/whatever/"
        )

    def test_post(self):
        request = self.request.post("/not/important/")
        self.assertEqual(
            request.build_absolute_uri("/whatever/"), "http://tenant1.localhost/whatever/"
        )

    def test_put(self):
        request = self.request.put("/not/important/")
        self.assertEqual(
            request.build_absolute_uri("/whatever/"), "http://tenant1.localhost/whatever/"
        )

    def test_patch(self):
        request = self.request.patch("/not/important/")
        self.assertEqual(
            request.build_absolute_uri("/whatever/"), "http://tenant1.localhost/whatever/"
        )

    def test_delete(self):
        request = self.request.delete("/not/important/")
        self.assertEqual(
            request.build_absolute_uri("/whatever/"), "http://tenant1.localhost/whatever/"
        )


class DynamicTenantClientTestCase(TestCase):
    """
    Test the behavior of the TenantClient with a dynamic tenant.
    """

    @classmethod
    def setUpClass(cls):
        if TenantModel is None:
            raise unittest.SkipTest("Dynamic tenants are not being used")

        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.localhost", is_primary=True)
        cls.tenant_client = TenantClient(tenant)

    @classmethod
    def tearDownClass(cls):
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


class StaticTenantClientTestCase(TestCase):
    """
    Test the behavior of the TenantClient with a static tenant.
    """

    @classmethod
    def setUpClass(cls):
        tenant = Schema.create(schema_name="blog", domain_url="blog.localhost")
        cls.tenant_client = TenantClient(tenant)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_get(self):
        response = self.tenant_client.get("/entries/")
        self.assertEqual(response.status_code, 200)

    def test_post(self):
        response = self.tenant_client.post("/entries/")
        self.assertEqual(response.status_code, 200)

    def test_put(self):
        response = self.tenant_client.put("/entries/")
        self.assertEqual(response.status_code, 200)

    def test_patch(self):
        response = self.tenant_client.patch("/entries/")
        self.assertEqual(response.status_code, 200)

    def test_delete(self):
        response = self.tenant_client.delete("/entries/")
        self.assertEqual(response.status_code, 200)
