import pytest


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
