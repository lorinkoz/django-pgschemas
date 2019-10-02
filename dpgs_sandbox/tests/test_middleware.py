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

    def test_static_tenants(self):
        # www
        request = self.factory.get("/", HTTP_HOST="www.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "www")
        self.assertEqual(modified_request.tenant.domain_url, "test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_main.urls")
        # blog
        request = self.factory.get("/some/random/url/", HTTP_HOST="blog.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "blog")
        self.assertEqual(modified_request.tenant.domain_url, "blog.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_blog.urls")

    def test_dynamic_tenants(self):
        # tenant1 by domain
        request = self.factory.get("/tenant2/", HTTP_HOST="tenant1.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "tenant1.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_tenants.urls")
        # tenant2 by domain
        request = self.factory.get("/tenant1/", HTTP_HOST="tenant2.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant2")
        self.assertEqual(modified_request.tenant.domain_url, "tenant2.test.com")
        self.assertEqual(modified_request.tenant.folder, None)
        self.assertEqual(modified_request.urlconf, "app_tenants.urls")
        # tenant1 by folder
        request = self.factory.get("/tenant1/some/random/url/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant1")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")
        # tenant2 by folder
        request = self.factory.get("/tenant2/some/random/url/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant2")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant2")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")
        # tenant1 by folder with short path
        request = self.factory.get("/tenant1/", HTTP_HOST="everyone.test.com")
        modified_request = self.middleware(request)
        self.assertTrue(modified_request.tenant)
        self.assertEqual(modified_request.tenant.schema_name, "tenant1")
        self.assertEqual(modified_request.tenant.domain_url, "everyone.test.com")
        self.assertEqual(modified_request.tenant.folder, "tenant1")
        self.assertEqual(modified_request.urlconf, "app_tenants.urls_dynamically_tenant_prefixed")
        # make sure on-the-fly urlconf can be imported
        import_module(modified_request.urlconf)
        # wrong subdomain
        request = self.factory.get("/some/random/url/", HTTP_HOST="bad-domain.test.com")
        with self.assertRaises(Http404):
            self.middleware(request)
        # wrong folder
        request = self.factory.get("/wrong-tenant/", HTTP_HOST="everyone.test.com")
        with self.assertRaises(Http404):
            self.middleware(request)
        # no folder
        request = self.factory.get("/", HTTP_HOST="everyone.test.com")
        with self.assertRaises(Http404):
            self.middleware(request)
