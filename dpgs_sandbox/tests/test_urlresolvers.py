import sys
from importlib import import_module

from django.test import RequestFactory, TestCase
from django.urls import reverse

from django_pgschemas.middleware import TenantMiddleware
from django_pgschemas.schema import Schema, activate_public
from django_pgschemas.urlresolvers import TenantPrefixPattern, get_urlconf_from_schema
from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class URLResolversTestCase(TestCase):
    """
    Tests TenantPrefixPattern and prefixed reverse.
    """

    @classmethod
    def setUpClass(cls):
        def reverser_func(self, name, domain, path="/"):
            """
            Reverses `name` in the urlconf returned by processing `domain` at `path`.
            """

            def fake_get_response(request):
                return request

            factory = RequestFactory()
            request = factory.get(path, HTTP_HOST=domain)
            modified_request = TenantMiddleware(fake_get_response)(request)
            with modified_request.tenant:
                urlconf = import_module(modified_request.urlconf)
                reverse_response = reverse(name, urlconf=urlconf)
                del sys.modules[modified_request.urlconf]  # required to simulate new thread
                return reverse_response

        cls.reverser = reverser_func
        # This comes from app_tenants/urls.py
        cls.paths = {"tenant-home": "/", "profile": "/profile/", "advanced-profile": "/profile/advanced/"}

        for i in range(1, 4):
            schema_name = f"tenant{i}"
            tenant = TenantModel(schema_name=schema_name)
            tenant.save(verbosity=0)
            DomainModel.objects.create(tenant=tenant, domain=f"{schema_name}.localhost")
            DomainModel.objects.create(tenant=tenant, domain="everyone.localhost", folder=schema_name)  # primary
        activate_public()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_tenant_prefix(self):
        tpp = TenantPrefixPattern()
        for tenant in TenantModel.objects.all():
            # Try with folder
            tenant.domain_url = "everyone.localhost"  # This should be set by middleware
            tenant.folder = tenant.schema_name  # This should be set by middleware
            with tenant:
                self.assertEqual(tpp.tenant_prefix, tenant.get_primary_domain().folder + "/")
            # Try with subdomain
            tenant.domain_url = f"{tenant.schema_name}.localhost"  # This should be set by middleware
            tenant.folder = ""  # This should be set by middleware
            with tenant:
                self.assertEqual(tpp.tenant_prefix, "/")
        with Schema.create(schema_name="tenant1", domain_url="unexisting-domain.localhost"):
            self.assertEqual(tpp.tenant_prefix, "/")

    def test_unprefixed_reverse(self):
        for tenant in TenantModel.objects.all():
            domain = f"{tenant.schema_name}.localhost"
            for name, path in self.paths.items():
                self.assertEqual(self.reverser(name, domain), path)

    def test_prefixed_reverse(self):
        for tenant in TenantModel.objects.all():
            domain = "everyone.localhost"
            for name, path in self.paths.items():
                self.assertEqual(self.reverser(name, domain, f"/{tenant.schema_name}/"), f"/{tenant.schema_name}{path}")


class URLConfFactoryTestCase(TestCase):
    """
    Tests get_urlconf_from_schema.
    """

    @classmethod
    def setUpClass(cls):
        schema_name = "tenant1"
        tenant = TenantModel(schema_name=schema_name)
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain=f"{schema_name}.localhost")
        DomainModel.objects.create(tenant=tenant, domain="everyone.localhost", folder=schema_name)  # primary
        activate_public()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_public(self):
        schema = Schema.create(schema_name="public")
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, None)

    def test_sample(self):
        schema = Schema.create(schema_name="sample")
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, None)

    def test_www(self):
        schema = Schema.create(schema_name="www", domain_url="localhost")
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, "app_main.urls")

    def test_blog(self):
        schema = Schema.create(schema_name="blog", domain_url="blog.localhost")
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, "app_blog.urls")

    def test_tenant1_unprefixed(self):
        schema = TenantModel.objects.get(schema_name="tenant1")
        schema.domain_url = "tenant1.localhost"
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, "app_tenants.urls")

    def test_tenant1_prefixed(self):
        schema = TenantModel.objects.get(schema_name="tenant1")
        schema.domain_url = "everyone.localhost"
        schema.folder = "tenant1"
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, "app_tenants.urls_dynamically_tenant_prefixed")
        self.assertTrue(sys.modules.get("app_tenants.urls_dynamically_tenant_prefixed"))

    def test_tenant1_broken_request(self):
        schema = TenantModel.objects.get(schema_name="tenant1")
        urlconf = get_urlconf_from_schema(schema)
        self.assertEqual(urlconf, None)
