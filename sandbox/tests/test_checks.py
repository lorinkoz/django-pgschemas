import pytest
from django.apps import apps
from django.core.checks import Critical, Error, Warning
from django.core.exceptions import ImproperlyConfigured

from django_pgschemas.checks import (
    check_other_apps,
    check_principal_apps,
    check_schema_names,
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
from django_pgschemas.utils import get_tenant_model


@pytest.fixture
def tenants(settings):
    from copy import deepcopy

    current = deepcopy(settings.TENANTS)

    yield settings.TENANTS

    settings.TENANTS.clear()
    settings.TENANTS.update(current)


@pytest.fixture
def app_config():
    return apps.get_app_config("django_pgschemas")


@pytest.fixture
def tenant_manager(db):
    TenantModel = get_tenant_model()

    if TenantModel is None:
        yield None
    else:
        backup = TenantModel.auto_create_schema
        TenantModel.auto_create_schema = False

        yield TenantModel._default_manager

        TenantModel.auto_create_schema = backup


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


class TestEnsurePublicSchema:
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


class TestEnsureDefaultSchema:
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


class TestEnsureOverallSchema:
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


class TestCheckPrincipalApps:
    BASE_DEFAULT = {"TENANT_MODEL": "shared_public.Tenant", "DOMAIN_MODEL": "shared_public.DOMAIN"}

    def test_location_wrong(self, tenants, app_config):
        tenants.update(
            {
                "public": {"APPS": []},
                "default": self.BASE_DEFAULT,
            }
        )
        expected_errors = [
            Error(
                "Your tenant app 'sandbox.shared_public' must be on the 'public' schema.",
                id="pgschemas.W001",
            ),
            Error(
                "Your domain app 'sandbox.shared_public' must be on the 'public' schema.",
                id="pgschemas.W001",
            ),
        ]

        errors = check_principal_apps(app_config)
        assert errors == expected_errors

    def test_location_twice(self, tenants, app_config):
        tenants.update(
            {
                "public": {"APPS": ["sandbox.shared_public"]},
                "default": {**self.BASE_DEFAULT, "APPS": ["sandbox.shared_public"]},
            }
        )

        expected_errors = [
            Error(
                "Your tenant app 'sandbox.shared_public' in TENANTS['default']['APPS'] "
                "must be on the 'public' schema only.",
                id="pgschemas.W001",
            ),
            Error(
                "Your domain app 'sandbox.shared_public' in TENANTS['default']['APPS'] "
                "must be on the 'public' schema only.",
                id="pgschemas.W001",
            ),
        ]

        errors = check_principal_apps(app_config)
        assert errors == expected_errors


class TestCheckOtherApps:
    def test_contenttypes_location_wrong(self, tenants, app_config):
        tenants.update(
            {
                "default": {"APPS": ["django.contrib.contenttypes"]},
            }
        )
        expected_errors = [
            Warning(
                "'django.contrib.contenttypes' in TENANTS['default']['APPS'] "
                "must be on 'public' schema only.",
                id="pgschemas.W002",
            )
        ]

        errors = check_other_apps(app_config)
        assert errors == expected_errors

    def test_contenttypes_location_twice(self, tenants, app_config):
        tenants.update(
            {
                "default": {},
                "www": {"APPS": ["django.contrib.contenttypes"]},
            }
        )
        expected_errors = [
            Warning(
                "'django.contrib.contenttypes' in TENANTS['www']['APPS'] "
                "must be on 'public' schema only.",
                id="pgschemas.W002",
            )
        ]

        errors = check_other_apps(app_config)
        assert errors == expected_errors

    def test_user_location_wrong(self, tenants, app_config):
        user_app = get_user_app()
        tenants.update(
            {
                "default": {"APPS": ["django.contrib.sessions"]},
            }
        )
        expected_errors = [
            Warning(
                f"'{user_app}' must be together with 'django.contrib.sessions' "
                "in TENANTS['default']['APPS'].",
                id="pgschemas.W003",
            )
        ]

        errors = check_other_apps(app_config)
        assert errors == expected_errors

    def test_session_location_wrong(self, tenants, app_config):
        user_app = get_user_app()
        tenants.update(
            {
                "www": {"APPS": ["shared_common", user_app]},
                "default": {"APPS": ["shared_common"]},
            }
        )
        expected_errors = [
            Warning(
                f"'django.contrib.sessions' must be together with '{user_app}' "
                "in TENANTS['www']['APPS'].",
                id="pgschemas.W003",
            )
        ]

        errors = check_other_apps(app_config)
        assert errors == expected_errors


@pytest.mark.parametrize("schema", ["public", "www", "blog", "sample"])
def test_check_schema_names(schema, app_config, tenant_manager):
    tenant_manager.create(schema_name=schema)
    expected_errors = [
        Critical(
            f"Name clash found between static and dynamic tenants: {{'{schema}'}}",
            id="pgschemas.W004",
        ),
    ]

    errors = check_schema_names(app_config)
    assert errors == expected_errors
