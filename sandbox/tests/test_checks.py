import pytest
from django.apps import apps
from django.core.checks import Critical, Error, Warning
from django.core.exceptions import ImproperlyConfigured

from django_pgschemas import checks


@pytest.fixture
def app_config():
    return apps.get_app_config("django_pgschemas")


@pytest.fixture
def tenant_manager(TenantModel, db):
    if TenantModel is None:
        yield None
    else:
        backup = TenantModel.auto_create_schema
        TenantModel.auto_create_schema = False

        yield TenantModel._default_manager

        TenantModel.auto_create_schema = backup


def test_get_tenant_app(tenants_settings, TenantModel):
    if TenantModel:
        assert checks.get_tenant_app() == "sandbox.shared_public"

        del tenants_settings["default"]

    assert checks.get_tenant_app() is None


def test_get_domain_app(tenants_settings, DomainModel):
    if DomainModel:
        assert checks.get_domain_app() == "sandbox.shared_public"

        del tenants_settings["default"]["DOMAIN_MODEL"]

    assert checks.get_domain_app() is None


def test_get_user_app(settings):
    assert checks.get_user_app() == "sandbox.shared_common"

    del settings.AUTH_USER_MODEL

    assert checks.get_user_app() is None


def test_get_session_app(settings):
    assert checks.get_session_app() == "django.contrib.sessions"


def test_ensure_tenant_dict(settings):
    backup = settings.TENANTS

    del settings.TENANTS

    with pytest.raises(ImproperlyConfigured) as ctx:
        checks.ensure_tenant_dict()

    assert str(ctx.value) == "TENANTS dict setting not set."

    settings.TENANTS = backup


class TestEnsurePublicSchema:
    @pytest.mark.parametrize("value", [None, "", 1])
    def test_no_dict(self, tenants_settings, value):
        tenants_settings["public"] = value

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_public_schema()

        assert str(ctx.value) == "TENANTS must contain a 'public' dict."

    @pytest.mark.parametrize(
        "member",
        [
            "URLCONF",
            "WS_URLCONF",
            "DOMAINS",
            "FALLBACK_DOMAINS",
            "SESSION_KEY",
            "HEADER",
        ],
    )
    def test_invalid_members(self, tenants_settings, member):
        tenants_settings["public"][member] = None

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_public_schema()

        assert str(ctx.value) == f"TENANTS['public'] cannot contain a '{member}' key."


class TestEnsureDefaultSchema:
    def test_static_only(self, tenants_settings):
        if "default" in tenants_settings:
            del tenants_settings["default"]

        checks.ensure_default_schemas()

    @pytest.mark.parametrize("value", [None, "", 1])
    def test_no_dict(self, tenants_settings, value):
        tenants_settings["default"] = value

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_default_schemas()

        assert str(ctx.value) == "TENANTS must contain a 'default' dict."

    @pytest.mark.parametrize(
        "member",
        [
            "DOMAINS",
            "FALLBACK_DOMAINS",
            "SESSION_KEY",
            "HEADER",
        ],
    )
    def test_invalid_members(self, tenants_settings, member):
        if "default" not in tenants_settings:
            pytest.skip("default not in tenant settings")

        tenants_settings["default"][member] = None

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_default_schemas()

        assert str(ctx.value) == f"TENANTS['default'] cannot contain a '{member}' key."

    @pytest.mark.parametrize(
        "member",
        [
            "TENANT_MODEL",
            "URLCONF",
        ],
    )
    def test_required_members(self, tenants_settings, member):
        if "default" not in tenants_settings:
            pytest.skip("default not in tenant settings")

        del tenants_settings["default"][member]

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_default_schemas()

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
    def test_clone_reference_invalid_name(self, tenants_settings, name):
        if "default" not in tenants_settings:
            pytest.skip("default not in tenant settings")

        tenants_settings["default"]["CLONE_REFERENCE"] = name

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_default_schemas()

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
    def test_invalid_names(self, tenants_settings, name):
        tenants_settings[name] = {}

        with pytest.raises(ImproperlyConfigured) as ctx:
            checks.ensure_overall_schemas()

        assert str(ctx.value) == f"'{name}' is not a valid schema name."


@pytest.mark.parametrize(
    "extra",
    [
        "public",
        "blog",
        "www",
        # "default",
    ],
)
def test_ensure_extra_search_paths(settings, extra, db):
    settings.PGSCHEMAS_EXTRA_SEARCH_PATHS = [extra]

    with pytest.raises(ImproperlyConfigured) as ctx:
        checks.ensure_extra_search_paths()

    invalid = ", ".join([extra])
    assert str(ctx.value) == f"Do not include '{invalid}' on PGSCHEMAS_EXTRA_SEARCH_PATHS."


class TestCheckPrincipalApps:
    BASE_DEFAULT = {"TENANT_MODEL": "shared_public.Tenant", "DOMAIN_MODEL": "shared_public.DOMAIN"}

    def test_location_wrong(self, tenants_settings, app_config):
        tenants_settings.update(
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

        errors = checks.check_principal_apps(app_config)
        assert errors == expected_errors

    def test_location_twice(self, tenants_settings, app_config):
        tenants_settings.update(
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

        errors = checks.check_principal_apps(app_config)
        assert errors == expected_errors


class TestCheckOtherApps:
    def test_contenttypes_location_wrong(self, tenants_settings, app_config):
        tenants_settings.update(
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

        errors = checks.check_other_apps(app_config)
        assert errors == expected_errors

    def test_contenttypes_location_twice(self, tenants_settings, app_config):
        tenants_settings.update(
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

        errors = checks.check_other_apps(app_config)
        assert errors == expected_errors

    def test_user_location_wrong(self, tenants_settings, app_config):
        user_app = checks.get_user_app()
        tenants_settings.update(
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

        errors = checks.check_other_apps(app_config)
        assert errors == expected_errors

    def test_session_location_wrong(self, tenants_settings, app_config):
        user_app = checks.get_user_app()
        tenants_settings.update(
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

        errors = checks.check_other_apps(app_config)
        assert errors == expected_errors


@pytest.mark.parametrize("schema", ["public", "www", "blog", "sample"])
def test_check_schema_names(schema, app_config, tenant_manager):
    if tenant_manager is None:
        pytest.skip("Dynamic tenants are not in use")

    tenant_manager.create(schema_name=schema)
    expected_errors = [
        Critical(
            f"Name clash found between static and dynamic tenants: {{'{schema}'}}",
            id="pgschemas.W004",
        ),
    ]

    errors = checks.check_schema_names(app_config)
    assert errors == expected_errors
