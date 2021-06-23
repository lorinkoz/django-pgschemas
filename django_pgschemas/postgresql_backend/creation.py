from ..utils import get_domain_model, get_tenant_model, get_test_domain, get_test_schema_name
from .settings import original_backend


class DatabaseCreation(original_backend.DatabaseCreation):
    def create_test_db(self, verbosity=1, autoclobber=False, serialize=True, keepdb=False):
        super().create_test_db(verbosity, autoclobber, serialize, keepdb)

        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()

        TEST_SCHEMA_NAME = get_test_schema_name()
        TEST_DOMAIN = get_test_domain()
        TEST_TENANT_DOMAIN = f"{TEST_SCHEMA_NAME}.{TEST_DOMAIN}"

        tenant = TenantModel.objects.filter(schema_name=TEST_SCHEMA_NAME).first()
        if not tenant:
            tenant = TenantModel(schema_name=TEST_SCHEMA_NAME)
            tenant.setup_for_test()
            tenant.save(verbosity=max(verbosity - 1, 0))

        domain = DomainModel.objects.filter(tenant=tenant, domain=TEST_TENANT_DOMAIN).first()
        if not domain:
            domain = DomainModel(tenant=tenant, domain=TEST_TENANT_DOMAIN)
            domain.setup_for_test()
            domain.save()
