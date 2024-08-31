from contextlib import contextmanager

import pytest
from django.apps import apps
from django.contrib.auth import authenticate
from django.db import ProgrammingError, transaction

from django_pgschemas.schema import Schema, deactivate
from django_pgschemas.signals import dynamic_tenant_post_sync
from django_pgschemas.utils import schema_exists


@pytest.fixture
def BlogEntryModel():
    return apps.get_model("app_blog.BlogEntry")


@pytest.fixture
def CatalogModel():
    return apps.get_model("shared_public.Catalog")


@pytest.fixture
def MainDataModel():
    return apps.get_model("app_main.MainData")


@pytest.fixture
def UserModel():
    return apps.get_model("shared_common.User")


@pytest.fixture
def TenantDataModel(TenantModel):
    return apps.get_model("app_tenants.TenantData") if TenantModel is not None else None


class ControlledException(Exception):
    pass


@contextmanager
def controlled_raises(exception):
    """
    Since we are expecting database errors, we must use savepoints in order
    to make sure multiple errors can be caught in the same test case.
    """
    sid = transaction.savepoint()

    with pytest.raises(exception):
        yield

    transaction.savepoint_rollback(sid)


class TestTenantAutomaticOperations:
    @pytest.fixture(autouse=True)
    def _setup(self, TenantModel):
        if TenantModel is None:
            pytest.skip("Dynamic tenants are not in use")

    def test_new_creation_deletion(self, TenantModel, db):
        assert not schema_exists("new_tenant1")

        tenant = TenantModel(schema_name="new_tenant1")
        tenant.save(verbosity=0)

        assert schema_exists("new_tenant1")

        tenant.delete(force_drop=True)

        assert not schema_exists("new_tenant1")

    def test_existing_creation(self, TenantModel, db):
        assert not schema_exists("new_tenant1")

        tenant = TenantModel(schema_name="new_tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)

        assert not schema_exists("new_tenant1")

        tenant.auto_create_schema = True
        tenant.save(verbosity=0)

        assert schema_exists("new_tenant1")

        tenant.delete(force_drop=True)

        assert not schema_exists("new_tenant1")

    def test_new_aborted_creation(self, TenantModel, db):
        def signal_receiver(*args, **kwargs):
            raise ControlledException

        assert not schema_exists("new_tenant1")

        tenant = TenantModel(schema_name="new_tenant1")
        dynamic_tenant_post_sync.connect(signal_receiver)

        with pytest.raises(ControlledException):
            tenant.save(verbosity=0)

        assert not schema_exists("new_tenant1")
        assert not TenantModel.objects.filter(schema_name="new_tenant1").exists()

        dynamic_tenant_post_sync.disconnect(signal_receiver)

    def test_existing_aborted_creation(self, TenantModel, db):
        def signal_receiver(*args, **kwargs):
            raise ControlledException

        assert not schema_exists("new_tenant1")

        tenant = TenantModel(schema_name="new_tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)

        tenant.auto_create_schema = True
        dynamic_tenant_post_sync.connect(signal_receiver)

        with pytest.raises(ControlledException):
            tenant.save(verbosity=0)

        assert not schema_exists("new_tenant1")
        assert TenantModel.objects.filter(schema_name="new_tenant1").exists()

        dynamic_tenant_post_sync.disconnect(signal_receiver)

        tenant.delete(force_drop=True)

        assert not TenantModel.objects.filter(schema_name="new_tenant1").exists()


class TestTenantIntegration:
    @pytest.fixture(autouse=True)
    def _setup(
        self, tenant1, CatalogModel, UserModel, MainDataModel, BlogEntryModel, TenantDataModel
    ):
        catalog = CatalogModel.objects.create()
        CatalogModel.objects.create()

        with Schema.create(schema_name="www"):
            user = UserModel.objects.create(email="main@localhost", display_name="Main User")
            user.set_password("weakpassword")
            user.save()
            MainDataModel.objects.create()

        with Schema.create(schema_name="blog"):
            user = UserModel.objects.create(email="blog@localhost", display_name="Blog User")
            user.set_password("weakpassword")
            user.save()
            BlogEntryModel.objects.create(user=user)

        if TenantDataModel is not None:
            with tenant1:
                user = UserModel.objects.create(
                    email="tenant@localhost", display_name="Tenant User"
                )
                user.set_password("weakpassword")
                user.save()
                TenantDataModel.objects.create(user=user, catalog=catalog)

    def test_migrated_public_apps(
        self, CatalogModel, UserModel, MainDataModel, BlogEntryModel, TenantDataModel
    ):
        deactivate()
        # Apps expected to be migrated

        assert CatalogModel.objects.count() == 2

        # Apps expected to NOT be migrated

        with controlled_raises(ProgrammingError):
            list(UserModel.objects.all())

        with controlled_raises(ProgrammingError):
            list(MainDataModel.objects.all())

        with controlled_raises(ProgrammingError):
            list(BlogEntryModel.objects.all())

        if TenantDataModel is not None:
            with controlled_raises(ProgrammingError):
                list(TenantDataModel.objects.all())

    def test_migrated_main_apps(
        self, CatalogModel, UserModel, MainDataModel, BlogEntryModel, TenantDataModel
    ):
        with Schema.create(schema_name="www"):
            # Apps expected to be migrated

            assert CatalogModel.objects.count() == 2
            assert UserModel.objects.count() == 1
            assert MainDataModel.objects.count() == 1

            # Apps expected to NOT be migrated

            with controlled_raises(ProgrammingError):
                list(BlogEntryModel.objects.all())

            if TenantDataModel is not None:
                with controlled_raises(ProgrammingError):
                    list(TenantDataModel.objects.all())

    def test_migrated_blog_apps(
        self, CatalogModel, UserModel, MainDataModel, BlogEntryModel, TenantDataModel
    ):
        with Schema.create(schema_name="blog"):
            # Apps expected to be migrated

            assert CatalogModel.objects.count() == 2
            assert UserModel.objects.count() == 1
            assert BlogEntryModel.objects.count() == 1

            # Direct and reverse relations
            assert UserModel.objects.first() == BlogEntryModel.objects.first().user
            assert UserModel.objects.first().blogs.first() == BlogEntryModel.objects.first()

            # Apps expected to NOT be migrated

            with controlled_raises(ProgrammingError):
                list(MainDataModel.objects.all())

            if TenantDataModel is not None:
                with controlled_raises(ProgrammingError):
                    list(TenantDataModel.objects.all())

    def test_migrated_tenant_apps(
        self, tenant1, CatalogModel, UserModel, MainDataModel, BlogEntryModel, TenantDataModel
    ):
        if not TenantDataModel:
            pytest.skip("Dynamic tenants are not in use")

        with tenant1:
            # Apps expected to be migrated

            assert CatalogModel.objects.count() == 2
            assert UserModel.objects.count() == 1
            assert TenantDataModel.objects.count() == 1

            # Direct and reverse relations
            assert UserModel.objects.first() == TenantDataModel.objects.first().user
            assert (
                UserModel.objects.first().tenant_objects.first() == TenantDataModel.objects.first()
            )
            assert CatalogModel.objects.first() == TenantDataModel.objects.first().catalog
            assert (
                CatalogModel.objects.first().tenant_objects.first()
                == TenantDataModel.objects.first()
            )

            # Apps expected to NOT be migrated

            with controlled_raises(ProgrammingError):
                list(MainDataModel.objects.all())

            with controlled_raises(ProgrammingError):
                list(BlogEntryModel.objects.all())

    def test_cross_authentication(self, tenant1, TenantModel):
        with Schema.create(schema_name="www"):
            assert authenticate(email="main@localhost", password="weakpassword")
            assert not authenticate(email="blog@localhost", password="weakpassword")
            assert not authenticate(email="tenant@localhost", password="weakpassword")

        with Schema.create(schema_name="blog"):
            assert not authenticate(email="main@localhost", password="weakpassword")
            assert authenticate(email="blog@localhost", password="weakpassword")
            assert not authenticate(email="tenant@localhost", password="weakpassword")

        if TenantModel is not None:
            with tenant1:
                assert not authenticate(email="main@localhost", password="weakpassword")
                assert not authenticate(email="blog@localhost", password="weakpassword")
                assert authenticate(email="tenant@localhost", password="weakpassword")

        with controlled_raises(ProgrammingError):
            authenticate(email="irrelevant@localhost", password="irrelevant")
