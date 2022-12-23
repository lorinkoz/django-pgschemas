from contextlib import contextmanager

from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.db import ProgrammingError, transaction
from django.test import TestCase

from django_pgschemas.schema import Schema, activate_public
from django_pgschemas.signals import dynamic_tenant_post_sync
from django_pgschemas.utils import drop_schema, get_domain_model, get_tenant_model, schema_exists

TenantModel = get_tenant_model()
DomainModel = get_domain_model()

BlogEntry = apps.get_model("app_blog.BlogEntry")
Catalog = apps.get_model("shared_public.Catalog")
MainData = apps.get_model("app_main.MainData")
TenantData = apps.get_model("app_tenants.TenantData")
User = apps.get_model("shared_common.User")


class TenantAutomaticTestCase(TestCase):
    """
    Tests tenant automatic operations.
    """

    def test_new_creation_deletion(self):
        "Tests automatic creation/deletion for new tenant's save/delete"
        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        self.assertTrue(schema_exists("tenant1"))
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertFalse(schema_exists("tenant1"))

    def test_existing_creation(self):
        "Tests automatic creation for existing tenant's save"
        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        tenant.auto_create_schema = True
        tenant.save(verbosity=0)
        self.assertTrue(schema_exists("tenant1"))
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertFalse(schema_exists("tenant1"))

    def test_new_aborted_creation(self):
        "Tests recovery on automatic creation for new tenant's save"

        def signal_receiver(*args, **kwargs):
            raise Exception

        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        dynamic_tenant_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(0, TenantModel.objects.count())
        dynamic_tenant_post_sync.disconnect(signal_receiver)

    def test_existing_aborted_creation(self):
        "Tests recovery on automatic creation for new tenant's save"

        def signal_receiver(*args, **kwargs):
            raise Exception

        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)
        tenant.auto_create_schema = True
        dynamic_tenant_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(1, TenantModel.objects.count())
        dynamic_tenant_post_sync.disconnect(signal_receiver)
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertEqual(0, TenantModel.objects.count())


class TenantTestCase(TestCase):
    """
    Tests cross tenant operations.
    """

    @classmethod
    def setUpClass(cls):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        catalog = Catalog.objects.create()
        Catalog.objects.create()
        with Schema.create(schema_name="www"):
            user = User.objects.create(email="main@localhost", display_name="Main User")
            user.set_password("weakpassword")
            user.save()
            MainData.objects.create()
        with Schema.create(schema_name="blog"):
            user = User.objects.create(email="blog@localhost", display_name="Blog User")
            user.set_password("weakpassword")
            user.save()
            BlogEntry.objects.create(user=user)
        with TenantModel.objects.first():
            user = User.objects.create(email="tenant@localhost", display_name="Tenant User")
            user.set_password("weakpassword")
            user.save()
            TenantData.objects.create(user=user, catalog=catalog)
        activate_public()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for key in settings.TENANTS:
            if key == "default":
                continue
            drop_schema(key)
        drop_schema("tenant")
        call_command("migrateschema", verbosity=0)

    @contextmanager
    def assertRaises(self, *args, **kwargs):
        """
        Since we are expecting database errors, we must use savepoints in order
        to make sure multiple errors can be caught in the same test case.
        """
        sid = transaction.savepoint()
        with super().assertRaises(*args, **kwargs):
            yield
        transaction.savepoint_rollback(sid)

    def test_synced_public_apps(self):
        # Expected synced apps
        self.assertEqual(2, Catalog.objects.count())
        # Not expected synced apps
        with self.assertRaises(ProgrammingError):
            list(User.objects.all())
        with self.assertRaises(ProgrammingError):
            list(MainData.objects.all())
        with self.assertRaises(ProgrammingError):
            list(BlogEntry.objects.all())
        with self.assertRaises(ProgrammingError):
            list(TenantData.objects.all())

    def test_synced_main_apps(self):
        with Schema.create(schema_name="www"):
            # Expected synced apps
            self.assertEqual(2, Catalog.objects.count())
            self.assertEqual(1, MainData.objects.count())
            self.assertEqual(1, User.objects.count())
            # Not expected synced apps
            with self.assertRaises(ProgrammingError):
                list(BlogEntry.objects.all())
            with self.assertRaises(ProgrammingError):
                list(TenantData.objects.all())

    def test_synced_blog_apps(self):
        with Schema.create(schema_name="blog"):
            # Expected synced apps
            self.assertEqual(2, Catalog.objects.count())
            self.assertEqual(1, BlogEntry.objects.count())
            self.assertEqual(1, User.objects.count())
            # Direct and reverse relations
            self.assertEqual(User.objects.first(), BlogEntry.objects.first().user)
            self.assertEqual(User.objects.first().blogs.first(), BlogEntry.objects.first())
            # Not expected synced apps
            with self.assertRaises(ProgrammingError):
                list(MainData.objects.all())
            with self.assertRaises(ProgrammingError):
                list(TenantData.objects.all())

    def test_synced_tenant_apps(self):
        with TenantModel.objects.first():
            # Expected synced apps
            self.assertEqual(2, Catalog.objects.count())
            self.assertEqual(1, TenantData.objects.count())
            self.assertEqual(1, User.objects.count())
            # Direct and reverse relations
            self.assertEqual(User.objects.first(), TenantData.objects.first().user)
            self.assertEqual(User.objects.first().tenant_objects.first(), TenantData.objects.first())
            self.assertEqual(Catalog.objects.first(), TenantData.objects.first().catalog)
            self.assertEqual(Catalog.objects.first().tenant_objects.first(), TenantData.objects.first())
            # Not expected synced apps
            with self.assertRaises(ProgrammingError):
                list(MainData.objects.all())
            with self.assertRaises(ProgrammingError):
                list(BlogEntry.objects.all())

    def test_cross_authentication(self):
        with Schema.create(schema_name="www"):
            self.assertTrue(authenticate(email="main@localhost", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="blog@localhost", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="tenant@localhost", password="weakpassword"))  # bad
        with Schema.create(schema_name="blog"):
            self.assertTrue(authenticate(email="blog@localhost", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="main@localhost", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="tenant@localhost", password="weakpassword"))  # bad
        with TenantModel.objects.first():
            self.assertTrue(authenticate(email="tenant@localhost", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="main@localhost", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="blog@localhost", password="weakpassword"))  # bad
        # Switching to public schema
        activate_public()
        with self.assertRaises(ProgrammingError):
            authenticate(email="unexisting@localhost", password="unexisting")  # unexisting, error


class DomainTestCase(TestCase):
    """
    Tests domain operations.
    """

    def test_primary_domain(self):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant2 = TenantModel(schema_name="tenant2")
        tenant1.save(verbosity=0)
        tenant2.save(verbosity=0)
        domain1 = DomainModel.objects.create(domain="tenant1.localhost", tenant=tenant1)
        DomainModel.objects.create(domain="tenant1-other.localhost", tenant=tenant1, is_primary=False)
        self.assertEqual(tenant1.get_primary_domain(), domain1)
        self.assertEqual(tenant2.get_primary_domain(), None)
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_domain_string(self):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        domain1 = DomainModel.objects.create(domain="tenant.localhost", tenant=tenant)
        domain2 = DomainModel.objects.create(domain="everyone.localhost", folder="tenant", tenant=tenant)
        self.assertEqual(str(domain1), "tenant.localhost")
        self.assertEqual(str(domain2), "everyone.localhost/tenant")
        tenant.delete(force_drop=True)

    def test_domain_absolute_url(self):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        subdomain = DomainModel.objects.create(domain="tenant.localhost", tenant=tenant)
        subfolder = DomainModel.objects.create(domain="everyone.localhost", folder="tenant", tenant=tenant)
        self.assertEqual(subdomain.absolute_url(""), "//tenant.localhost/")
        self.assertEqual(subdomain.absolute_url("/some/path/"), "//tenant.localhost/some/path/")
        self.assertEqual(subdomain.absolute_url("some/path"), "//tenant.localhost/some/path")
        self.assertEqual(subfolder.absolute_url(""), "//everyone.localhost/tenant/")
        self.assertEqual(subfolder.absolute_url("/some/path/"), "//everyone.localhost/tenant/some/path/")
        self.assertEqual(subfolder.absolute_url("some/path"), "//everyone.localhost/tenant/some/path")
        tenant.delete(force_drop=True)

    def test_domain_redirect_save(self):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        domain = DomainModel.objects.create(domain="tenant.localhost", tenant=tenant, redirect_to_primary=True)
        self.assertTrue(domain.is_primary)
        self.assertFalse(domain.redirect_to_primary)
        tenant.delete(force_drop=True)
