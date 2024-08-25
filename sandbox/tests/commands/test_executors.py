import pytest
from django.core import management

from sandbox.shared_public.models import Domain, Tenant


@pytest.fixture(autouse=True)
def _setup(db):
    tenants = []

    for i in range(10, 20):
        tenant = Tenant(schema_name=f"tenant{i + 1}")
        tenant.save(verbosity=0)
        Domain.objects.create(tenant=tenant, domain=f"tenant{i + 1}.localhost", is_primary=True)

        tenants.append(tenant)

    yield

    for tenant in tenants:
        tenant.delete(force_drop=True)


def test_all_schemas_in_sequential():
    # If there are no errors, then this test passed
    management.call_command("migrate", all_schemas=True, parallel=False, verbosity=0)


@pytest.mark.skip(reason="Fails for some OS")
def test_all_schemas_in_parallel():
    # If there are no errors, then this test passed
    management.call_command("migrate", all_schemas=True, parallel=True, verbosity=0)
