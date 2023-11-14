import pytest

from sandbox.shared_public.models import Tenant


@pytest.fixture(scope="session", autouse=True)
def setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        Tenant.objects.get_or_create(schema_name="tenant1")
        Tenant.objects.get_or_create(schema_name="tenant2")
        Tenant.objects.get_or_create(schema_name="tenant3")


@pytest.fixture
def settings_tenants(settings):
    from copy import deepcopy

    current = deepcopy(settings.TENANTS)

    yield settings.TENANTS

    settings.TENANTS.clear()
    settings.TENANTS.update(current)


@pytest.fixture(params=["static-only", "tenants-no-domains", "tenants-and-domains"])
def variable_settings_tenants(request, settings_tenants):
    if request.param == "static-only":
        del settings_tenants["default"]
    if request.param == "tenants-no-domains":
        del settings_tenants["default"]["DOMAIN_MODEL"]

    yield settings_tenants


@pytest.fixture
def tenant1(db):
    return Tenant.objects.get(schema_name="tenant1")


@pytest.fixture
def tenant2(db):
    return Tenant.objects.get(schema_name="tenant2")


@pytest.fixture
def tenant3(db):
    return Tenant.objects.get(schema_name="tenant3")
