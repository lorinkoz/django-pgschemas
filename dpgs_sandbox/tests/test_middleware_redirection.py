from django.test import RequestFactory, TestCase

from django_pgschemas.middleware import TenantMiddleware
from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class TenantMiddlewareRedirectionTestCase(TestCase):
    """
    Tests TenantMiddlewareRedirection.
    """

    @classmethod
    def setUpTestData(cls):
        def fake_get_response(request):
            return request

        cls.factory = RequestFactory()
        cls.middleware = TenantMiddleware(fake_get_response)
        tenant1 = TenantModel(schema_name="tenant1")
        tenant2 = TenantModel(schema_name="tenant2")
        tenant1.auto_create_schema = tenant2.auto_create_schema = False
        tenant1.save()
        tenant2.save()

        DomainModel(domain="tenant1.test.com", tenant=tenant1).save()
        DomainModel(
            domain="tenant1redirect.test.com", tenant=tenant1, is_primary=False, redirect_to_primary=True
        ).save()
        DomainModel(
            domain="everyone.test.com",
            folder="tenant1redirect",
            tenant=tenant1,
            is_primary=False,
            redirect_to_primary=True,
        ).save()

        DomainModel(domain="everyone.test.com", folder="tenant2", tenant=tenant2).save()
        DomainModel(
            domain="tenant2redirect.test.com", tenant=tenant2, is_primary=False, redirect_to_primary=True
        ).save()
        DomainModel(
            domain="everyone.test.com",
            folder="tenant2redirect",
            tenant=tenant2,
            is_primary=False,
            redirect_to_primary=True,
        ).save()

    def test_domain_redirect_to_primary_domain(self):
        request = self.factory.get("/some/random/url/", HTTP_HOST="tenant1redirect.test.com")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "//tenant1.test.com/some/random/url/")
        self.assertEqual(response["Location"], "//tenant1.test.com/some/random/url/")

    def test_folder_redirect_to_primary_domain(self):
        request = self.factory.get("/tenant1redirect/some/random/url/", HTTP_HOST="everyone.test.com")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "//tenant1.test.com/some/random/url/")
        self.assertEqual(response["Location"], "//tenant1.test.com/some/random/url/")

    def test_domain_redirect_to_primary_folder(self):
        request = self.factory.get("/some/random/url/", HTTP_HOST="tenant2redirect.test.com")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "//everyone.test.com/tenant2/some/random/url/")
        self.assertEqual(response["Location"], "//everyone.test.com/tenant2/some/random/url/")

    def test_folder_redirect_to_primary_folder(self):
        request = self.factory.get("/tenant2redirect/some/random/url/", HTTP_HOST="everyone.test.com")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, "//everyone.test.com/tenant2/some/random/url/")
        self.assertEqual(response["Location"], "//everyone.test.com/tenant2/some/random/url/")