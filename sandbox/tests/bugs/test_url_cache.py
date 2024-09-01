import pytest
from django.apps import apps
from django.test import Client


@pytest.fixture
def UserModel():
    return apps.get_model("shared_common.User")


@pytest.fixture(autouse=True)
def _setup(tenant1, tenant2, DomainModel, UserModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    DomainModel.objects.create(
        tenant=tenant1, domain="everyone.localhost", folder="tenant1", is_primary=True
    )
    DomainModel.objects.create(
        tenant=tenant2, domain="everyone.localhost", folder="tenant2", is_primary=True
    )
    with tenant1:
        UserModel.objects.create(email="user1@localhost", display_name="Admin")

    with tenant2:
        UserModel.objects.create(email="user2@localhost", display_name="Admin")


@pytest.fixture
def client():
    return Client(headers={"host": "everyone.localhost"})


@pytest.mark.bug
def test_bug_in_cached_urls_1(client):
    # Provoke redirect to login on tenant2
    client.get("/tenant2/profile/advanced/")

    # Provoke redirect to login on tenant1
    buggy_response = client.get("/tenant1/profile/advanced/")

    assert buggy_response.status_code == 302
    assert buggy_response.url == "/tenant1/login/?next=/tenant1/profile/advanced/"


@pytest.mark.bug
def test_bug_in_cached_urls_2(client):
    # Provoke redirect to login on tenant1
    client.get("/tenant1/profile/advanced/")

    # Provoke redirect to login on tenant2
    buggy_response = client.get("/tenant2/profile/advanced/")

    assert buggy_response.status_code == 302
    assert buggy_response.url == "/tenant2/login/?next=/tenant2/profile/advanced/"
