from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core import management
from django.db import connection

from django_pgschemas.schema import Schema


@pytest.fixture(autouse=True)
def _require_dynamic_tenants(TenantModel):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")


@pytest.fixture
def many_tenants(TenantModel, DomainModel, transactional_db):
    """
    Parallel workers cannot see rows that only exist inside an uncommitted
    test transaction, so these tenants are created under transactional_db.
    """
    tenants = []

    for i in range(10, 20):
        tenant = TenantModel(schema_name=f"tenant{i + 1}")
        tenant.save(verbosity=0)
        if DomainModel:
            DomainModel.objects.create(
                tenant=tenant, domain=f"tenant{i + 1}.localhost", is_primary=True
            )
        tenants.append(tenant)

    assert _tenant_visible_to_worker(tenants[0].schema_name), (
        f"{tenants[0].schema_name} is not visible to a worker thread; "
        "parallel migrate requires committed tenants"
    )

    yield tenants

    for tenant in tenants:
        tenant.delete(force_drop=True)


def _tenant_visible_to_worker(schema_name: str) -> bool:
    def worker() -> bool:
        from django.db import connections

        from django_pgschemas.utils import get_tenant_model

        try:
            TenantModel = get_tenant_model()
            assert TenantModel is not None
            return TenantModel.objects.filter(schema_name=schema_name).exists()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(worker).result()


def _migration_count(schema_name: str) -> int:
    with Schema.create(schema_name=schema_name):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            return cursor.fetchone()[0]


def test_all_schemas_in_sequential(many_tenants):
    management.call_command("migrate", all_schemas=True, parallel=False, verbosity=0)
    assert _migration_count("tenant11") > 0


def test_all_schemas_in_parallel(many_tenants):
    management.call_command("migrate", all_schemas=True, parallel=True, verbosity=0)
    assert _migration_count("tenant11") > 0
    assert _migration_count("tenant20") > 0
