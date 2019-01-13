import sys
from importlib import import_module

from django.db import connection
from django.test import TestCase, RequestFactory
from django.urls import reverse

from django_pgschemas.middleware import TenantMiddleware
from django_pgschemas.schema import SchemaDescriptor
from django_pgschemas.urlresolvers import TenantPrefixPattern
from django_pgschemas.utils import get_tenant_model, get_domain_model

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
        cls.paths = {"home": "/", "profile": "/profile/", "advanced-profile": "/profile/advanced/"}

        for i in range(1, 4):
            schema_name = "tenant{}".format(i)
            tenant = TenantModel(schema_name=schema_name)
            tenant.auto_create_schema = True
            tenant.save(verbosity=0)
            DomainModel.objects.create(tenant=tenant, domain="{}.test.com".format(schema_name))
            DomainModel.objects.create(tenant=tenant, domain="everything.test.com", folder=schema_name)  # primary
        connection.set_schema_to_public()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for tenant in TenantModel.objects.all():
            tenant.auto_drop_schema = True
            tenant.delete(force_drop=True)

    def test_tenant_prefix(self):
        tpp = TenantPrefixPattern()
        for tenant in TenantModel.objects.all():
            # Try with folder
            tenant.domain_url = "everything.test.com"  # This should be set by middleware
            with tenant:
                self.assertEqual(tpp.tenant_prefix, tenant.get_primary_domain().folder + "/")
            # Try with subdomain
            tenant.domain_url = "{}.test.com".format(tenant.schema_name)  # This should be set by middleware
            with tenant:
                self.assertEqual(tpp.tenant_prefix, "/")
        with SchemaDescriptor.create(schema_name="tenant1", domain_url="unexisting-domain.test.com"):
            self.assertEqual(tpp.tenant_prefix, "/")

    def test_unprefixed_reverse(self):
        for tenant in TenantModel.objects.all():
            domain = "{}.test.com".format(tenant.schema_name)
            for name, path in self.paths.items():
                self.assertEqual(self.reverser(name, domain), path)

    def test_prefixed_reverse(self):
        for tenant in TenantModel.objects.all():
            domain = "everything.test.com"
            for name, path in self.paths.items():
                self.assertEqual(
                    self.reverser(name, domain, "/{}/".format(tenant.schema_name)),
                    "/{}{}".format(tenant.schema_name, path),
                )
