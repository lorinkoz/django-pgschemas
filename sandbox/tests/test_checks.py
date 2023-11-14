import pytest
from django.core.exceptions import ImproperlyConfigured

from django_pgschemas.checks import (
    ensure_default_schemas,
    ensure_extra_search_paths,
    ensure_overall_schemas,
    ensure_public_schema,
    ensure_tenant_dict,
    get_domain_app,
    get_session_app,
    get_tenant_app,
    get_user_app,
)


@pytest.fixture
def tenants(settings):
    from copy import deepcopy

    current = deepcopy(settings.TENANTS)

    yield settings.TENANTS

    settings.TENANTS.clear()
    settings.TENANTS.update(current)


def test_get_tenant_app(tenants):
    assert get_tenant_app() == "sandbox.shared_public"

    del tenants["default"]

    assert get_tenant_app() is None


def test_get_domain_app(tenants):
    assert get_domain_app() == "sandbox.shared_public"

    del tenants["default"]["DOMAIN_MODEL"]

    assert get_domain_app() is None


def test_get_user_app(settings):
    assert get_user_app() == "sandbox.shared_common"

    del settings.AUTH_USER_MODEL

    assert get_user_app() is None


def test_get_session_app(settings):
    assert get_session_app() == "django.contrib.sessions"


def test_ensure_tenant_dict(settings):
    del settings.TENANTS

    with pytest.raises(ImproperlyConfigured) as ctx:
        ensure_tenant_dict()

    assert str(ctx.value) == "TENANTS dict setting not set."


class Test_ensure_public_schema:
    @pytest.mark.parametrize("value", [None, "", 1])
    def test_no_dict(self, tenants, value):
        tenants["public"] = value

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_public_schema()

        assert str(ctx.value) == "TENANTS must contain a 'public' dict."

    @pytest.mark.parametrize(
        "member",
        [
            "URLCONF",
            "WS_URLCONF",
            "DOMAINS",
            "FALLBACK_DOMAINS",
        ],
    )
    def test_invalid_members(self, tenants, member):
        tenants["public"][member] = None

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_public_schema()

        assert str(ctx.value) == f"TENANTS['public'] cannot contain a '{member}' key."


class Test_ensure_default_schemas:
    def test_static_only(self, tenants):
        del tenants["default"]

        ensure_default_schemas()

    @pytest.mark.parametrize("value", [None, "", 1])
    def test_no_dict(self, tenants, value):
        tenants["default"] = value

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_default_schemas()

        assert str(ctx.value) == "TENANTS must contain a 'default' dict."

    @pytest.mark.parametrize(
        "member",
        [
            "DOMAINS",
            "FALLBACK_DOMAINS",
        ],
    )
    def test_invalid_members(self, tenants, member):
        tenants["default"][member] = None

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_default_schemas()

        assert str(ctx.value) == f"TENANTS['default'] cannot contain a '{member}' key."

    @pytest.mark.parametrize(
        "member",
        [
            "TENANT_MODEL",
            "URLCONF",
        ],
    )
    def test_required_members(self, tenants, member):
        del tenants["default"][member]

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_default_schemas()

        assert str(ctx.value) == f"TENANTS['default'] must contain a '{member}' key."

    @pytest.mark.parametrize(
        "name",
        [
            "public",
            "default",
            "blog",
            "www",
        ],
    )
    def test_clone_reference_invalid_name(self, tenants, name):
        tenants["default"]["CLONE_REFERENCE"] = name

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_default_schemas()

        assert (
            str(ctx.value) == "TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name."
        )


class Test_ensure_overall_schemas:
    @pytest.mark.parametrize(
        "name",
        [
            "pg_something",
            "1something",
            ".something",
            "-something",
            "tomanycharacters0123456789abcdef0123456789abcef0123456789abcdef0",
        ],
    )
    def test_invalid_names(self, tenants, name):
        tenants[name] = {}

        with pytest.raises(ImproperlyConfigured) as ctx:
            ensure_overall_schemas()

        assert str(ctx.value) == f"'{name}' is not a valid schema name."


@pytest.mark.parametrize(
    "extra",
    [
        "public",
        "default",
        "blog",
        "www",
    ],
)
def test_ensure_extra_search_paths(settings, extra, db):
    settings.PGSCHEMAS_EXTRA_SEARCH_PATHS = [extra]

    with pytest.raises(ImproperlyConfigured) as ctx:
        ensure_extra_search_paths()

    invalid = ", ".join([extra])
    assert str(ctx.value) == f"Do not include '{invalid}' on PGSCHEMAS_EXTRA_SEARCH_PATHS."
