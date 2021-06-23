from django.core import management
from django.db import connections
from django.test import TransactionTestCase

from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class ExecutorsTestCase(TransactionTestCase):
    """
    Tests the executors.
    """

    @classmethod
    def setUpClass(cls):
        for i in range(10):
            tenant = TenantModel(schema_name=f"tenant{i + 1}")
            tenant.save(verbosity=0)
            DomainModel.objects.create(tenant=tenant, domain=f"tenant{i + 1}.sandbox.com", is_primary=True)

    @classmethod
    def tearDownClass(cls):
        for tenant in TenantModel.objects.filter(schema_name__icontains="tenant"):
            tenant.delete(force_drop=True)

    def test_all_schemas_in_sequential(self):
        # If there are no errors, then this test passed
        management.call_command("migrate", all_schemas=True, parallel=False, verbosity=0)
        connections.close_all()

    def test_all_schemas_in_parallel(self):
        # If there are no errors, then this test passed
        management.call_command("migrate", all_schemas=True, parallel=True, verbosity=0)
        connections.close_all()
