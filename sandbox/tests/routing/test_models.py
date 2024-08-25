import pytest

from django_pgschemas.routing.models import get_primary_domain_for_tenant


@pytest.fixture(autouse=True)
def _setup(DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")


@pytest.mark.parametrize(
    "domain, folder, expected",
    [
        ("tenants.localhost", "", "tenants.localhost"),
        ("tenants.localhost", "tenant1", "tenants.localhost/tenant1"),
    ],
)
def test_str(tenant1, domain, folder, expected, DomainModel):
    item = DomainModel.objects.create(
        tenant=tenant1,
        domain=domain,
        folder=folder,
    )

    assert str(item) == expected


def test_only_one_primary(tenant1, DomainModel):
    domain1 = DomainModel.objects.create(
        tenant=tenant1,
        domain="tenant1.localhost",
        folder="",
        is_primary=True,
    )

    assert domain1.is_primary

    domain2 = DomainModel.objects.create(
        tenant=tenant1,
        domain="tenants.localhost",
        folder="tenant1",
        is_primary=True,
    )

    domain1.refresh_from_db()

    assert not domain1.is_primary
    assert domain2.is_primary


@pytest.mark.parametrize("is_primary", [True, False])
def test_redirect_to_primary_if_primary(tenant1, is_primary, DomainModel):
    domain1 = DomainModel.objects.create(
        domain="tenant1.localhost",
        folder="",
        is_primary=is_primary,
        redirect_to_primary=True,
        tenant=tenant1,
    )

    assert domain1.redirect_to_primary is not domain1.is_primary


@pytest.mark.parametrize(
    "domain, folder, path, expected",
    [
        ("tenants.localhost", "", "", "//tenants.localhost/"),
        ("tenants.localhost", "tenant1", "", "//tenants.localhost/tenant1/"),
        ("tenants.localhost", "tenant1", "some/path", "//tenants.localhost/tenant1/some/path"),
        ("tenants.localhost", "tenant1", "/some/path", "//tenants.localhost/tenant1/some/path"),
        ("tenants.localhost", "tenant1", "/some/path/", "//tenants.localhost/tenant1/some/path/"),
    ],
)
def test_absolute_url(tenant1, domain, folder, path, expected, DomainModel):
    item = DomainModel.objects.create(
        tenant=tenant1,
        domain=domain,
        folder=folder,
    )

    assert item.absolute_url(path) == expected


@pytest.mark.parametrize("is_primary", [True, False, None])
def test_get_primary_domain_for_tenant(tenant1, is_primary, DomainModel):
    if is_primary is not None:
        item = DomainModel.objects.create(
            tenant=tenant1,
            domain="tenant1.localhost",
        )
        DomainModel.objects.update(is_primary=is_primary)
        item.refresh_from_db()

    if is_primary:
        assert get_primary_domain_for_tenant(tenant1) == item
    else:
        assert get_primary_domain_for_tenant(tenant1) is None
