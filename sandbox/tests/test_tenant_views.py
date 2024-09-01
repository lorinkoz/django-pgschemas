import pytest
from django.apps import apps
from django.test import Client

from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.schema import Schema


@pytest.fixture
def UserModel():
    return apps.get_model("shared_common.User")


@pytest.fixture(autouse=True)
def _setup(UserModel, db):
    with Schema.create("www"):
        UserModel.objects.create(email="user_www@localhost", display_name="Admin")

    with Schema.create("blog"):
        UserModel.objects.create(email="user_blog@localhost", display_name="Admin")


@pytest.fixture
def _setup_dynamic(tenant1, UserModel, DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    DomainModel.objects.create(tenant=tenant1, domain="tenant1.localhost", is_primary=True)
    DomainModel.objects.create(tenant=tenant1, domain="everyone.localhost", folder="tenant1")

    with tenant1:
        yield UserModel.objects.create(email="user1@localhost", display_name="Admin")


@pytest.mark.parametrize(
    "url, expected_status",
    [
        ("/", 200),
        ("/register/", 200),
        ("/admin/", 302),
        ("/non-existing/", 404),
    ],
)
def test_views_www(url, expected_status):
    client = Client(headers={"host": "localhost"})

    response = client.get(url)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "url, expected_status",
    [
        ("/", 200),
        ("/entries/", 200),
        ("/admin/", 302),
        ("/non-existing/", 404),
    ],
)
def test_views_blog(url, expected_status):
    client = Client(headers={"host": "blog.localhost"})

    response = client.get(url)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "url, expected_status",
    [
        ("/", 200),
        ("/profile/", 200),
        ("/profile/advanced/", 302),
        ("/login/", 200),
        ("/admin/", 302),
        ("/non-existing/", 404),
    ],
)
def test_tenants_domain(url, expected_status, _setup_dynamic):
    user = _setup_dynamic
    client = Client(headers={"host": "tenant1.localhost"})

    response = client.get(url)

    assert response.status_code == expected_status

    if expected_status == "200":
        assert response.context == {
            "path": url,
            "user": user,
            "schema": "tenant1",
            "routing": DomainInfo(domain="tenant1.localhost", folder=""),
            "admin_url": "/admin/",
        }


@pytest.mark.parametrize(
    "url, expected_status",
    [
        ("/tenant1/", 200),
        ("/tenant1/profile/", 200),
        ("/tenant1/profile/advanced/", 302),
        ("/tenant1/login/", 200),
        ("/tenant1/admin/", 302),
        ("/tenant1/non-existing/", 404),
    ],
)
def test_tenants_folder(url, expected_status, _setup_dynamic):
    user = _setup_dynamic
    client = Client(headers={"host": "everyone.localhost"})

    response = client.get(url)

    assert response.status_code == expected_status

    if expected_status == "200":
        assert response.context == {
            "path": url,
            "user": user,
            "schema": "tenant1",
            "routing": DomainInfo(domain="everyone.localhost", folder="tenant1"),
            "admin_url": "/tenant1/admin/",
        }
