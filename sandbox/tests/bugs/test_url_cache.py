import pytest
from django.apps import apps
from django.test import Client

User = apps.get_model("shared_common.User")


@pytest.fixture(autouse=True)
def _setup(tenant1, tenant2, DomainModel):
    DomainModel.objects.create(
        tenant=tenant1, domain="everyone.localhost", folder="tenant1", is_primary=True
    )
    DomainModel.objects.create(
        tenant=tenant2, domain="everyone.localhost", folder="tenant2", is_primary=True
    )
    with tenant1:
        User.objects.create(email="user1@localhost", display_name="Admin")

    with tenant2:
        User.objects.create(email="user2@localhost", display_name="Admin")


@pytest.fixture
def client1():
    return Client(headers={"host": "everyone.localhost"})


@pytest.mark.bug
class CachedTenantSubfolderBugTestCase:
    """
    Tests the behavior of subfolder routing regarding caching of URL patterns.
    This test checks that a bug reported in issue #8.
    """

    def test_bug_in_cached_urls_1(self, client):
        client.get("/tenant2/profile/advanced/")  # Provoke redirect to login on tenant2
        buggy_response = client.get(
            "/tenant1/profile/advanced/"
        )  # Provoke redirect to login on tenant1

        buggy_response.status_code == 302
        buggy_response.url == "/tenant1/login/?next=/tenant1/profile/advanced/"

    def test_bug_in_cached_urls_2(self, client):
        client.get("/tenant1/profile/advanced/")  # Provoke redirect to login on tenant1
        buggy_response = client.get(
            "/tenant2/profile/advanced/"
        )  # Provoke redirect to login on tenant2

        buggy_response.status_code == 302
        buggy_response.url == "/tenant2/login/?next=/tenant2/profile/advanced/"
