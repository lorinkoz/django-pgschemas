from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from ..schema import SchemaDescriptor, activate, activate_public
from ..utils import get_clone_reference, get_domain_model, get_tenant_model

ALLOWED_TEST_DOMAIN = ".localhost"


class BaseTenantTestCaseMixin:
    @classmethod
    def get_verbosity(cls):
        return 0

    @classmethod
    def add_allowed_test_domain(cls):
        cls.BACKUP_ALLOWED_HOSTS = settings.ALLOWED_HOSTS
        # ALLOWED_HOSTS is a special setting of Django setup_test_environment so we can't modify it with helpers
        if ALLOWED_TEST_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [ALLOWED_TEST_DOMAIN]

    @classmethod
    def remove_allowed_test_domain(cls):
        settings.ALLOWED_HOSTS = cls.BACKUP_ALLOWED_HOSTS

    @classmethod
    def sync_public(cls):
        call_command("migrateschema", schemas=["public"], verbosity=0)


class StaticTenantTestCase(BaseTenantTestCaseMixin, TestCase):
    schema_name = None  # Meant to be set by subclasses
    tenant = None

    @classmethod
    def setUpClass(cls):
        assert (
            cls.schema_name in settings.TENANTS
        ), f"{cls.__name__}.schema_name must be defined to a valid static tenant"
        assert (
            cls.schema_name not in ["public", "default"] and cls.schema_name != get_clone_reference()
        ), f"{cls.__name__}.schema_name must be defined to a valid static tenant"
        super(TestCase, cls).setUpClass()
        cls.sync_public()
        cls.add_allowed_test_domain()
        domain = (
            settings.TENANTS[cls.schema_name]["DOMAINS"][0]
            if settings.TENANTS[cls.schema_name]["DOMAINS"]
            else cls.schema_name + ALLOWED_TEST_DOMAIN
        )
        cls.tenant = SchemaDescriptor.create(schema_name=cls.schema_name, domain_url=domain)
        activate(cls.tenant)
        cls.cls_atomics = cls._enter_atomics()
        try:
            cls.setUpTestData()
        except Exception:
            cls._rollback_atomics(cls.cls_atomics)
            raise

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        activate_public()
        cls.remove_allowed_test_domain()


class DynamicTenantTestCase(BaseTenantTestCaseMixin, TestCase):
    tenant = None
    domain = None

    @classmethod
    def setup_tenant(cls, tenant):
        """
        Add any additional setting to the tenant before it get saved. This is required if you have
        required fields.
        :param tenant:
        :return:
        """
        pass

    @classmethod
    def setup_domain(cls, domain):
        """
        Add any additional setting to the domain before it get saved. This is required if you have
        required fields.
        :param domain:
        :return:
        """
        pass

    @classmethod
    def setUpClass(cls):
        super(TestCase, cls).setUpClass()
        cls.sync_public()
        cls.add_allowed_test_domain()
        cls.tenant = get_tenant_model()(schema_name=cls.get_test_schema_name())
        cls.setup_tenant(cls.tenant)
        cls.tenant.save(verbosity=cls.get_verbosity())
        tenant_domain = cls.get_test_tenant_domain()
        cls.domain = get_domain_model()(tenant=cls.tenant, domain=tenant_domain)
        cls.setup_domain(cls.domain)
        cls.domain.save()
        activate(cls.tenant)
        cls.cls_atomics = cls._enter_atomics()
        try:
            cls.setUpTestData()
        except Exception:
            cls._rollback_atomics(cls.cls_atomics)
            raise

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        activate_public()
        cls.domain.delete()
        cls.tenant.delete(force_drop=True)
        cls.remove_allowed_test_domain()

    @classmethod
    def get_test_tenant_domain(cls):
        return "tenant.localhost"

    @classmethod
    def get_test_schema_name(cls):
        return "test"


class TenantTestCase(DynamicTenantTestCase):
    pass


class FastDynamicTenantTestCase(DynamicTenantTestCase):
    @classmethod
    def flush_data(cls):
        """
        Do you want to flush the data out of the tenant database.
        :return: bool
        """
        return True

    @classmethod
    def use_existing_tenant(cls):
        """
        Gets called if a existing tenant is found in the database
        """
        pass

    @classmethod
    def use_new_tenant(cls):
        """
        Gets called if a new tenant is created in the database
        """
        pass

    @classmethod
    def setup_test_tenant_and_domain(cls):
        cls.tenant = get_tenant_model()(schema_name=cls.get_test_schema_name())
        cls.setup_tenant(cls.tenant)
        cls.tenant.save(verbosity=cls.get_verbosity())

        # Set up domain
        tenant_domain = cls.get_test_tenant_domain()
        cls.domain = get_domain_model()(tenant=cls.tenant, domain=tenant_domain)
        cls.setup_domain(cls.domain)
        cls.domain.save()
        cls.use_new_tenant()

    @classmethod
    def setUpClass(cls):
        TenantModel = get_tenant_model()
        test_schema_name = cls.get_test_schema_name()
        if TenantModel.objects.filter(schema_name=test_schema_name).exists():
            cls.tenant = TenantModel.objects.filter(schema_name=test_schema_name).first()
            cls.use_existing_tenant()
        else:
            cls.setup_test_tenant_and_domain()

        activate(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        TenantModel = get_tenant_model()
        test_schema_name = cls.get_test_schema_name()
        TenantModel.objects.filter(schema_name=test_schema_name).delete()
        activate_public()

    def _fixture_teardown(self):
        if self.flush_data():
            super()._fixture_teardown()


class FastTenantTestCase(FastDynamicTenantTestCase):
    pass
