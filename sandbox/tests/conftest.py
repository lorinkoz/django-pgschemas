from io import StringIO

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup(django_db_setup, django_db_blocker):
    from sandbox.shared_public.models import Tenant

    with django_db_blocker.unblock():
        Tenant.objects.get_or_create(schema_name="tenant1")
        Tenant.objects.get_or_create(schema_name="tenant2")
        Tenant.objects.get_or_create(schema_name="tenant3")


@pytest.fixture(autouse=True, params=["static-only", "tenants-no-domains", "tenants-and-domains"])
def tenants_settings(request, settings):
    from copy import deepcopy

    current = deepcopy(settings.TENANTS)

    if request.param == "static-only":
        del settings.TENANTS["default"]

    if request.param == "tenants-no-domains":
        del settings.TENANTS["default"]["DOMAIN_MODEL"]

    yield settings.TENANTS

    settings.TENANTS.clear()
    settings.TENANTS.update(current)


@pytest.fixture
def TenantModel():
    from django_pgschemas.utils import get_tenant_model

    return get_tenant_model()


@pytest.fixture
def DomainModel():
    from django_pgschemas.utils import get_domain_model

    return get_domain_model()


@pytest.fixture
def tenant1(db):
    from sandbox.shared_public.models import Tenant

    return Tenant.objects.get(schema_name="tenant1")


@pytest.fixture
def tenant2(db):
    from sandbox.shared_public.models import Tenant

    return Tenant.objects.get(schema_name="tenant2")


@pytest.fixture
def tenant3(db):
    from sandbox.shared_public.models import Tenant

    return Tenant.objects.get(schema_name="tenant3")


@pytest.fixture
def stdout():
    with StringIO() as buffer:
        yield buffer
