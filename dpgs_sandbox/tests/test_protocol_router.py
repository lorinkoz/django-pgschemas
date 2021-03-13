from django.test import TestCase

from django_pgschemas.contrib.channels2 import TenantProtocolRouter
from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class TenantProtocolRouterTestCase(TestCase):
    """
    Tests TenantProtocolRouter.
    """

    @classmethod
    def setUpClass(cls):
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.test.com", is_primary=True)
        DomainModel.objects.create(tenant=tenant, domain="everyone.test.com", folder="tenant1", is_primary=False)
        cls.tenant = tenant
        cls.router = TenantProtocolRouter()

    @classmethod
    def tearDownClass(cls):
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_get_tenant_scope_static(self):
        scope = {"path": "/", "headers": [(b"host", b"blog.test.com")]}
        tenant, tenant_prefix, ws_urlconf = self.router.get_tenant_scope(scope)
        self.assertEqual(tenant.schema_name, "blog")
        self.assertEqual(tenant_prefix, "")
        self.assertEqual(ws_urlconf, [])

    def test_get_tenant_scope_dynamic_subdomain(self):
        scope = {"path": "/", "headers": [(b"host", b"tenant1.test.com")]}
        tenant, tenant_prefix, ws_urlconf = self.router.get_tenant_scope(scope)
        self.assertEqual(tenant, self.tenant)
        self.assertEqual(tenant_prefix, "")
        self.assertEqual(ws_urlconf, [])

    def test_get_tenant_scope_dynamic_subfolder(self):
        scope = {"path": "/tenant1/", "headers": [(b"host", b"everyone.test.com")]}
        tenant, tenant_prefix, ws_urlconf = self.router.get_tenant_scope(scope)
        self.assertEqual(tenant, self.tenant)
        self.assertEqual(tenant_prefix, "tenant1")
        self.assertEqual(ws_urlconf, [])

    def test_get_tenant_scope_dynamic_failed(self):
        scope = {"path": "/", "headers": [(b"host", b"unknown-tenant.test.com")]}
        tenant, tenant_prefix, ws_urlconf = self.router.get_tenant_scope(scope)
        self.assertEqual(tenant, None)
        self.assertEqual(tenant_prefix, "")
        self.assertEqual(ws_urlconf, [])


class TenantAwareProtocolTypeRouterTestCase(TestCase):
    """
    Tests TenantAwareProtocolTypeRouter.
    """

    @classmethod
    def setUpClass(cls):
        cls.router = TenantProtocolRouter()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_response_good(self):
        scope = {"path": "/", "headers": [(b"host", b"test.com")], "type": "websocket"}
        self.assertTrue(self.router(scope))

    def test_response_bad(self):
        scope = {"path": "/non-existent/", "headers": [(b"host", b"test.com")], "type": "websocket"}
        with self.assertRaises(ValueError):
            self.router(scope)
