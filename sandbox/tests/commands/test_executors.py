import pytest
from django.core import management


@pytest.fixture(autouse=True)
def _setup(TenantModel, DomainModel, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    tenants = []

    for i in range(10, 20):
        tenant = TenantModel(schema_name=f"tenant{i + 1}")
        tenant.save(verbosity=0)
        if DomainModel:
            DomainModel.objects.create(
                tenant=tenant, domain=f"tenant{i + 1}.localhost", is_primary=True
            )

        tenants.append(tenant)

    yield

    for tenant in tenants:
        tenant.delete(force_drop=True)


def test_all_schemas_in_sequential():
    # If there are no errors, then this test passed
    management.call_command("migrate", all_schemas=True, parallel=False, verbosity=0)


def test_all_schemas_in_parallel():
    # If there are no errors, then this test passed
    management.call_command("migrate", all_schemas=True, parallel=True, verbosity=0)
