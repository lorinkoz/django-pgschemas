from importlib import import_module

from django.http import Http404
from django.test import TestCase, RequestFactory
from django.utils.module_loading import import_string

from django_pgschemas.middleware import TenantMiddleware
from django_pgschemas.utils import get_tenant_model, get_domain_model


class TenantMiddlewareTestCase(TestCase):
    """
    Tests TenantMiddleware.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()

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
        DomainModel(domain="everyone.test.com", folder="tenant1", tenant=tenant1).save()
        DomainModel(domain="tenant2.test.com", tenant=tenant2).save()
        DomainModel(domain="everyone.test.com", folder="tenant2", tenant=tenant2).save()
        DomainModel(domain="special.test.com", folder="tenant2", tenant=tenant2).save()

    def test_static_tenants_www(self):
        request = self.factory.get("/", HTTP_HOST="www.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "www")
        self.assertEqual(modified_request.tenant.domain_url, "test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_main.urls")

    def test_static_tenants_blog(self):
        request = self.factory.get("/some/random/url/", HTTP_HOST="blog.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "blog")
        self.assertEqual(modified_request.tenant.domain_url, "blog.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_blog.urls")

    def test_dynamic_tenants_tenant1_domain(self):
        request = self.factory.get("/tenant2/", HTTP_HOST="tenant1.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "tenant1.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_tenants.urls")

    def test_dynamic_tenants_tenant2_domain(self):
        request = self.factory.get("/tenant1/", HTTP_HOST="tenant2.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant2")
        self.assertEqual(modified_request.tenant.domain_url, "tenant2.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_tenants.urls")

    def test_dynamic_tenants_tenant1_folder(self):
        request = self.factory.get("/tenant1/some/random/url/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant1")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")

    def test_dynamic_tenants_tenant2_folder(self):
        request = self.factory.get("/tenant2/some/random/url/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant2")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant2")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")

    def test_dynamic_tenants_tenant1_folder_short(self):
        request = self.factory.get("/tenant1/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant1")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")

    def test_dynamic_module_can_be_imported(self):
        request = self.factory.get("/tenant1/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        import_module(modified_request.urlconf)

    def test_wrong_subdomain(self):
        request = self.factory.get("/some/random/url/", HTTP_HOST="bad-domain.test.com")
        with self.assertRaises(Http404):
            self.middleware(request)

    def test_no_folder(self):
        request = self.factory.get("/", HTTP_HOST="special.test.com")
        with self.assertRaises(Http404):
            self.middleware(request)

    def test_fallback_domain_root(self):
        request = self.factory.get("/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "www")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_main.urls")

    def test_fallback_domain_folder(self):
        request = self.factory.get("/some/random/url/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "www")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_main.urls")
