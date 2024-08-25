from unittest.mock import patch

import pytest
from django.core import management
from django.core.management.base import CommandError

from django_pgschemas.management.commands import CommandScope
from django_pgschemas.management.commands.whowill import Command as WhoWillCommand


@pytest.fixture(autouse=True)
def _setup(tenant1, tenant2, TenantModel, DomainModel):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    if DomainModel:
        DomainModel.objects.create(
            tenant=tenant1,
            domain="tenant1.localhost",
            is_primary=True,
        )
        DomainModel.objects.create(
            tenant=tenant1,
            domain="everyone.localhost",
            folder="tenant1",
            is_primary=False,
        )
        DomainModel.objects.create(
            tenant=tenant2,
            domain="tenant2.localhost",
            is_primary=True,
        )
        DomainModel.objects.create(
            tenant=tenant2,
            domain="everyone.localhost",
            folder="tenant2",
            is_primary=False,
        )


def test_no_schema_provided():
    command = WhoWillCommand()

    with pytest.raises(CommandError) as ctx:
        management.call_command(command, interactive=False, verbosity=0)

    assert str(ctx.value) == "No schema provided"


def test_no_all_schemas_allowed():
    command = WhoWillCommand()
    command.allow_wildcards = False

    with pytest.raises(TypeError):
        management.call_command(command, all_schemas=True, verbosity=0)


def test_no_static_schemas_allowed():
    command = WhoWillCommand()
    command.scope = CommandScope.DYNAMIC

    with pytest.raises(CommandError) as ctx:
        management.call_command(command, static_schemas=True, verbosity=0)

    assert str(ctx.value) == "Including static schemas is NOT allowed"

    command = WhoWillCommand()
    command.allow_wildcards = False

    with pytest.raises(TypeError):
        management.call_command(command, static_schemas=True, verbosity=0)


def test_no_dynamic_schemas_allowed():
    command = WhoWillCommand()
    command.scope = CommandScope.STATIC

    with pytest.raises(CommandError) as ctx:
        management.call_command(command, dynamic_schemas=True, verbosity=0)

    assert str(ctx.value) == "Including dynamic schemas is NOT allowed"

    command = WhoWillCommand()
    command.allow_wildcards = False

    with pytest.raises(TypeError):
        management.call_command(command, dynamic_schemas=True, verbosity=0)


def test_no_tenant_like_schemas_allowed():
    command = WhoWillCommand()
    command.scope = CommandScope.STATIC

    with pytest.raises(CommandError) as ctx:
        management.call_command(command, tenant_schemas=True, verbosity=0)

    assert str(ctx.value) == "Including tenant-like schemas is NOT allowed"

    command = WhoWillCommand()
    command.allow_wildcards = False

    with pytest.raises(TypeError):
        management.call_command(command, tenant_schemas=True, verbosity=0)


def test_nonexisting_schema():
    with pytest.raises(CommandError) as ctx:
        management.call_command("whowill", schemas=["unknown"], verbosity=0)

    assert str(ctx.value) == "No schema found for 'unknown'"


def test_ambiguous_schema(DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    with pytest.raises(CommandError) as ctx:
        management.call_command("whowill", schemas=["tenant"], verbosity=0)

    assert (
        str(ctx.value)
        == "More than one tenant found for schema 'tenant' by domain, please, narrow down the filter"
    )


def test_specific_schemas():
    command = WhoWillCommand()
    command.specific_schemas = ["blog"]

    with pytest.raises(CommandError) as ctx:
        management.call_command(command, schemas=["www"], verbosity=0)

    assert str(ctx.value) == "This command can only run in ['blog']"


def test_nonexisting_schema_excluded():
    with pytest.raises(CommandError) as ctx:
        management.call_command(
            "whowill", all_schemas=True, excluded_schemas=["unknown"], verbosity=0
        )

    assert str(ctx.value) == "No schema found for 'unknown' (excluded)"


def test_ambiguous_schema_excluded(DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    with pytest.raises(CommandError) as ctx:
        management.call_command(
            "whowill", all_schemas=True, excluded_schemas=["tenant"], verbosity=0
        )

    assert (
        str(ctx.value)
        == "More than one tenant found for schema 'tenant' by domain (excluded), please, narrow down the filter"
    )


def test_existing_schema_excluded_ok():
    management.call_command("whowill", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0)


def test_interactive_ok():
    def patched_input(*args, **kwargs):
        return "blog"

    with patch("builtins.input", patched_input):
        management.call_command("whowill", schemas=[], verbosity=0)


def test_interactive_nonexisting():
    def patched_input(*args, **kwargs):
        return "unknown"

    with patch("builtins.input", patched_input):
        with pytest.raises(CommandError) as ctx:
            management.call_command("whowill", schemas=[], verbosity=0)

        assert str(ctx.value) == "No schema found for 'unknown'"


def test_mixed_ok(DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    management.call_command("whowill", all_schemas=True, verbosity=0)
    management.call_command("whowill", static_schemas=True, verbosity=0)
    management.call_command("whowill", dynamic_schemas=True, verbosity=0)
    management.call_command("whowill", tenant_schemas=True, verbosity=0)
    management.call_command("whowill", schemas=["public", "sample"], verbosity=0)
    management.call_command(
        "whowill",
        all_schemas=True,
        static_schemas=True,
        dynamic_schemas=True,
        tenant_schemas=True,
        schemas=["public", "sample"],
        verbosity=0,
    )
    management.call_command(
        "whowill", all_schemas=True, excluded_schemas=["public", "sample"], verbosity=0
    )
    management.call_command("whowill", schemas=["everyone.localhost/tenant1"], verbosity=0)
    management.call_command("whowill", schemas=["tenant1"], verbosity=0)
    management.call_command(
        "whowill",
        all_schemas=True,
        excluded_schemas=["everyone.localhost/tenant1"],
        verbosity=0,
    )
    management.call_command("whowill", all_schemas=True, excluded_schemas=["tenant1"], verbosity=0)
