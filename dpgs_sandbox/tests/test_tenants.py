from contextlib import contextmanager

from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.db import ProgrammingError, transaction
from django.test import TestCase, TransactionTestCase

from django_pgschemas.schema import SchemaDescriptor, schema_handler
from django_pgschemas.signals import schema_post_sync
from django_pgschemas.utils import drop_schema, get_domain_model, get_tenant_model, schema_exists

TenantModel = get_tenant_model()
DomainModel = get_domain_model()

BlogEntry = apps.get_model("app_blog.BlogEntry")
Catalog = apps.get_model("shared_public.Catalog")
MainData = apps.get_model("app_main.MainData")
TenantData = apps.get_model("app_tenants.TenantData")
User = apps.get_model("shared_common.User")


class TenantAutomaticTestCase(TransactionTestCase):
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
        schema_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(0, TenantModel.objects.count())
        schema_post_sync.disconnect(signal_receiver)

    def test_existing_aborted_creation(self):
        "Tests recovery on automatic creation for new tenant's save"

        def signal_receiver(*args, **kwargs):
            raise Exception

        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)
        tenant.auto_create_schema = True
        schema_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(1, TenantModel.objects.count())
        schema_post_sync.disconnect(signal_receiver)
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
        with SchemaDescriptor.create(schema_name="www"):
            user = User.objects.create(email="main@test.com", display_name="Main User")
            user.set_password("weakpassword")
            user.save()
            MainData.objects.create()
        with SchemaDescriptor.create(schema_name="blog"):
            user = User.objects.create(email="blog@test.com", display_name="Blog User")
            user.set_password("weakpassword")
            user.save()
            BlogEntry.objects.create(user=user)
        with TenantModel.objects.first():
            user = User.objects.create(email="tenant@test.com", display_name="Tenant User")
            user.set_password("weakpassword")
            user.save()
            TenantData.objects.create(user=user, catalog=catalog)
        schema_handler.set_schema_to_public()
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
        with SchemaDescriptor.create(schema_name="www"):
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
        with SchemaDescriptor.create(schema_name="blog"):
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
        with SchemaDescriptor.create(schema_name="www"):
            self.assertTrue(authenticate(email="main@test.com", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="blog@test.com", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="tenant@test.com", password="weakpassword"))  # bad
        with SchemaDescriptor.create(schema_name="blog"):
            self.assertTrue(authenticate(email="blog@test.com", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="main@test.com", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="tenant@test.com", password="weakpassword"))  # bad
        with TenantModel.objects.first():
            self.assertTrue(authenticate(email="tenant@test.com", password="weakpassword"))  # good
            self.assertFalse(authenticate(email="main@test.com", password="weakpassword"))  # bad
            self.assertFalse(authenticate(email="blog@test.com", password="weakpassword"))  # bad
        # Switching to public schema
        TenantModel.deactivate_all()
        with self.assertRaises(ProgrammingError):
            authenticate(email="unexisting@test.com", password="unexisting")  # unexisting, error


class DomainTestCase(TransactionTestCase):
    """
    Tests domain operations.
    """

    def test_primary_domain(self):
        tenant1 = TenantModel(schema_name="tenant1")
        tenant2 = TenantModel(schema_name="tenant2")
        tenant1.save(verbosity=0)
        tenant2.save(verbosity=0)
        domain1 = DomainModel.objects.create(domain="tenant1.test.com", tenant=tenant1)
        DomainModel.objects.create(domain="tenant1-other.test.com", tenant=tenant1, is_primary=False)
        self.assertEqual(tenant1.get_primary_domain(), domain1)
        self.assertEqual(tenant2.get_primary_domain(), None)
        for tenant in TenantModel.objects.all():
            tenant.delete(force_drop=True)

    def test_domain_string(self):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        domain1 = DomainModel.objects.create(domain="tenant.test.com", tenant=tenant)
        domain2 = DomainModel.objects.create(domain="everyone.test.com", folder="tenant", tenant=tenant)
        self.assertEqual(str(domain1), "tenant.test.com")
        self.assertEqual(str(domain2), "everyone.test.com/tenant")
        tenant.delete(force_drop=True)

    def test_domain_absolute_url(self):
        tenant = TenantModel(schema_name="tenant")
        tenant.save(verbosity=0)
        subdomain = DomainModel.objects.create(domain="tenant.test.com", tenant=tenant)
        subfolder = DomainModel.objects.create(domain="everyone.test.com", folder="tenant", tenant=tenant)
        self.assertEqual(subdomain.absolute_url(""), "//tenant.test.com/")
        self.assertEqual(subdomain.absolute_url("/some/path/"), "//tenant.test.com/some/path/")
        self.assertEqual(subdomain.absolute_url("some/path"), "//tenant.test.com/some/path")
        self.assertEqual(subfolder.absolute_url(""), "//everyone.test.com/tenant/")
        self.assertEqual(subfolder.absolute_url("/some/path/"), "//everyone.test.com/tenant/some/path/")
        self.assertEqual(subfolder.absolute_url("some/path"), "//everyone.test.com/tenant/some/path")
        tenant.delete(force_drop=True)
