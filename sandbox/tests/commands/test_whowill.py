import pytest
from django.core import management

from sandbox.shared_public.models import Domain


@pytest.fixture(autouse=True)
def _setup(tenant1, tenant2, tenant3):
    for tenant in [tenant1, tenant2, tenant3]:
        Domain.objects.create(
            tenant=tenant, domain=f"{tenant.schema_name}.localhost", is_primary=True
        )


def split_output(buffer):
    buffer.seek(0)
    return set(buffer.read().strip().splitlines())


def test_all_schemas(stdout, db):
    management.call_command("whowill", all_schemas=True, stdout=stdout)

    assert split_output(stdout) == {
        "public",
        "sample",
        "localhost",
        "blog.localhost",
        "tenant1.localhost",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_static_schemas(stdout, db):
    management.call_command("whowill", static_schemas=True, stdout=stdout)

    assert split_output(stdout) == {"public", "sample", "localhost", "blog.localhost"}


def test_tenant_like_schemas(stdout, db):
    management.call_command("whowill", tenant_schemas=True, stdout=stdout)

    assert split_output(stdout) == {
        "sample",
        "tenant1.localhost",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_dynamic_schemas(stdout, db):
    management.call_command("whowill", dynamic_schemas=True, stdout=stdout)

    assert split_output(stdout) == {
        "tenant1.localhost",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_specific_schemas(stdout, db):
    management.call_command("whowill", schemas=["www", "blog", "tenant1"], stdout=stdout)

    assert split_output(stdout) == {
        "localhost",
        "blog.localhost",
        "tenant1.localhost",
    }


# Same test cases as before, but excluding one


def test_all_schemas_minus_one(stdout, db):
    management.call_command("whowill", all_schemas=True, excluded_schemas=["blog"], stdout=stdout)

    assert split_output(stdout) == {
        "public",
        "sample",
        "localhost",
        "tenant1.localhost",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_static_schemas_minus_one(stdout, db):
    management.call_command(
        "whowill", static_schemas=True, excluded_schemas=["sample"], stdout=stdout
    )

    assert split_output(stdout) == {"public", "localhost", "blog.localhost"}


def test_tenant_like_schemas_minus_one(stdout, db):
    management.call_command(
        "whowill", tenant_schemas=True, excluded_schemas=["tenant1"], stdout=stdout
    )

    assert split_output(stdout) == {
        "sample",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_dynamic_schemas_minus_one(stdout, db):
    management.call_command(
        "whowill", dynamic_schemas=True, excluded_schemas=["public"], stdout=stdout
    )

    assert split_output(stdout) == {
        "tenant1.localhost",
        "tenant2.localhost",
        "tenant3.localhost",
    }


def test_specific_schemas_minus_one(stdout, db):
    management.call_command(
        "whowill",
        schemas=["www", "blog", "tenant1"],
        excluded_schemas=["www"],
        stdout=stdout,
    )

    assert split_output(stdout) == {
        "blog.localhost",
        "tenant1.localhost",
    }
