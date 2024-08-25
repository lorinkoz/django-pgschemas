import pytest
from django.core import management


@pytest.fixture(autouse=True)
def _setup(tenant1, tenant2, tenant3, TenantModel, DomainModel):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    if DomainModel:
        for tenant in [tenant1, tenant2, tenant3]:
            DomainModel.objects.create(
                tenant=tenant, domain=f"{tenant.schema_name}.localhost", is_primary=True
            )


def split_output(buffer):
    buffer.seek(0)
    return set(buffer.read().strip().splitlines())


def test_all_schemas(DomainModel, stdout):
    management.call_command("whowill", all_schemas=True, stdout=stdout)

    expected_dynamic = (
        {"tenant1.localhost", "tenant2.localhost", "tenant3.localhost"}
        if DomainModel
        else {"tenant1", "tenant2", "tenant3"}
    )

    assert (
        split_output(stdout)
        == {"public", "sample", "localhost", "blog.localhost"} | expected_dynamic
    )


def test_static_schemas(stdout):
    management.call_command("whowill", static_schemas=True, stdout=stdout)

    assert split_output(stdout) == {"public", "sample", "localhost", "blog.localhost"}


def test_tenant_like_schemas(DomainModel, stdout):
    management.call_command("whowill", tenant_schemas=True, stdout=stdout)

    expected_dynamic = (
        {"tenant1.localhost", "tenant2.localhost", "tenant3.localhost"}
        if DomainModel
        else {"tenant1", "tenant2", "tenant3"}
    )

    assert split_output(stdout) == {"sample"} | expected_dynamic


def test_dynamic_schemas(DomainModel, stdout):
    management.call_command("whowill", dynamic_schemas=True, stdout=stdout)

    expected_dynamic = (
        {"tenant1.localhost", "tenant2.localhost", "tenant3.localhost"}
        if DomainModel
        else {"tenant1", "tenant2", "tenant3"}
    )

    assert split_output(stdout) == expected_dynamic


def test_specific_schemas(DomainModel, stdout):
    management.call_command("whowill", schemas=["www", "blog", "tenant1"], stdout=stdout)

    expected_dynamic = {"tenant1.localhost"} if DomainModel else {"tenant1"}

    assert split_output(stdout) == {"localhost", "blog.localhost"} | expected_dynamic


# Same test cases as before, but excluding one


def test_all_schemas_minus_one(DomainModel, stdout):
    management.call_command("whowill", all_schemas=True, excluded_schemas=["blog"], stdout=stdout)

    expected_dynamic = (
        {
            "tenant1.localhost",
            "tenant2.localhost",
            "tenant3.localhost",
        }
        if DomainModel
        else {"tenant1", "tenant2", "tenant3"}
    )

    assert split_output(stdout) == {"public", "sample", "localhost"} | expected_dynamic


def test_static_schemas_minus_one(stdout):
    management.call_command(
        "whowill", static_schemas=True, excluded_schemas=["sample"], stdout=stdout
    )

    assert split_output(stdout) == {"public", "localhost", "blog.localhost"}


def test_tenant_like_schemas_minus_one(DomainModel, stdout):
    management.call_command(
        "whowill", tenant_schemas=True, excluded_schemas=["tenant1"], stdout=stdout
    )

    expected_dynamic = (
        {"tenant2.localhost", "tenant3.localhost"} if DomainModel else {"tenant2", "tenant3"}
    )

    assert split_output(stdout) == {"sample"} | expected_dynamic


def test_dynamic_schemas_minus_one(DomainModel, stdout):
    management.call_command(
        "whowill", dynamic_schemas=True, excluded_schemas=["public"], stdout=stdout
    )

    expected_dynamic = (
        {
            "tenant1.localhost",
            "tenant2.localhost",
            "tenant3.localhost",
        }
        if DomainModel
        else {
            "tenant1",
            "tenant2",
            "tenant3",
        }
    )

    assert split_output(stdout) == expected_dynamic


def test_specific_schemas_minus_one(DomainModel, stdout):
    management.call_command(
        "whowill",
        schemas=["www", "blog", "tenant1"],
        excluded_schemas=["www"],
        stdout=stdout,
    )

    expected_dynamic = {"tenant1.localhost"} if DomainModel else {"tenant1"}

    assert split_output(stdout) == {"blog.localhost"} | expected_dynamic
