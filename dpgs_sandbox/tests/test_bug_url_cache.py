from unittest.mock import patch

from django.apps import apps
from django.test import TransactionTestCase, tag
from django.urls import reverse

from django_pgschemas.test.client import TenantClient
from django_pgschemas.utils import get_tenant_model, get_domain_model

User = apps.get_model("shared_common.User")


@tag("bug")
class CachedTenantSubfolderBugTestCase(TransactionTestCase):
    """
    Tests the behavior of subfolder routing regarding caching of URL patterns.
    This test checks that a bug reported in issue #8.
    """

    @classmethod
    def setUpClass(cls):
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()
        tenant1 = TenantModel(schema_name="tenant1")
        tenant1.save(verbosity=0)
        tenant2 = TenantModel(schema_name="tenant2")
        tenant2.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant1, domain="everyone.test.com", folder="tenant1", is_primary=True)
        DomainModel.objects.create(tenant=tenant2, domain="everyone.test.com", folder="tenant2", is_primary=True)
        with tenant1:
            cls.user1 = User.objects.create(email="user1@test.com", display_name="Admin")
        with tenant2:
            cls.user2 = User.objects.create(email="user2@test.com", display_name="Admin")
        cls.client1 = TenantClient(tenant1)
        cls.client2 = TenantClient(tenant2)

    @classmethod
    def tearDownClass(cls):
        TenantModel = get_tenant_model()
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    @patch("django_pgschemas.middleware.clear_url_caches", lambda: None)
    def test_bug_in_cached_urls_fail(self):
        self.client1.get("/tenant1/profile/advanced/")  # Provoke redirect to login on tenant1
        buggy_response = self.client2.get("/tenant2/profile/advanced/")  # Provoke redirect to login on tenant2
        self.assertEqual(buggy_response.status_code, 302)
        self.assertEqual(buggy_response.url, "/tenant1/login/?next=/tenant2/profile/advanced/")

    def test_bug_in_cached_urls_success(self):
        self.client1.get("/tenant1/profile/advanced/")  # Provoke redirect to login on tenant1
        buggy_response = self.client2.get("/tenant2/profile/advanced/")  # Provoke redirect to login on tenant2
        self.assertEqual(buggy_response.status_code, 302)
        self.assertEqual(buggy_response.url, "/tenant2/login/?next=/tenant2/profile/advanced/")
