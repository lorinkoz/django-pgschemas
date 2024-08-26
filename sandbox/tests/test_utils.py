import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import DatabaseError

from django_pgschemas import schema, utils

VALID_IDENTIFIERS = ["___", "a_a0", "_a0_", "a" * 63]
INVALID_IDENTIFIERS = ["", " ", "^", ".", "&", "{", "(", "@", "!", "a" * 64]
VALID_SCHEMA_NAMES = ["a_pg", "w_pg_a", "_pg_awa", "pgwa"] + VALID_IDENTIFIERS
INVALID_SCHEMA_NAMES = ["pg_a", "pg_"] + INVALID_IDENTIFIERS


def test_get_tenant_model(tenants_settings):
    TenantModel = utils.get_tenant_model()

    if "default" in tenants_settings:
        assert TenantModel is not None
        assert TenantModel._meta.model_name == "tenant"
    else:
        assert TenantModel is None


def test_get_domain_model(tenants_settings):
    DomainModel = utils.get_domain_model()

    if "default" in tenants_settings and "DOMAIN_MODEL" in tenants_settings["default"]:
        assert DomainModel is not None
        assert DomainModel._meta.model_name == "domain"
    else:
        assert DomainModel is None


@pytest.mark.parametrize("has_value", [True, False])
def test_get_tenant_database_alias(settings, has_value):
    if has_value:
        settings.PGSCHEMAS_TENANT_DB_ALIAS = "something"
        assert utils.get_tenant_database_alias() == "something"
    else:
        assert utils.get_tenant_database_alias() == "default"


@pytest.mark.parametrize("has_value", [True, False])
def test_get_limit_set_calls(settings, has_value):
    if has_value:
        settings.PGSCHEMAS_LIMIT_SET_CALLS = True
        assert utils.get_limit_set_calls()
    else:
        assert not utils.get_limit_set_calls()


def test_get_clone_reference(tenants_settings):
    clone_reference = utils.get_clone_reference()

    if "default" in tenants_settings:
        assert clone_reference == "sample"
    else:
        assert clone_reference is None


@pytest.mark.parametrize(
    "identifier, is_valid",
    [(identifier, True) for identifier in VALID_IDENTIFIERS]
    + [(identifier, False) for identifier in INVALID_IDENTIFIERS],
)
def test_is_valid_identifier(identifier, is_valid):
    assert utils.is_valid_identifier(identifier) == is_valid


@pytest.mark.parametrize(
    "name, is_valid",
    [(name, True) for name in VALID_SCHEMA_NAMES]
    + [(name, False) for name in INVALID_SCHEMA_NAMES],
)
def test_is_valid_schema_name(name, is_valid):
    assert utils.is_valid_schema_name(name) == is_valid


@pytest.mark.parametrize(
    "name, is_valid",
    [(name, True) for name in VALID_SCHEMA_NAMES]
    + [(name, False) for name in INVALID_SCHEMA_NAMES],
)
def test_check_schema_name(name, is_valid):
    if is_valid:
        utils.check_schema_name(name)
    else:
        with pytest.raises(ValidationError):
            utils.check_schema_name(name)


def test_run_in_public_schema(db):
    @utils.run_in_public_schema
    def inner():
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            assert cursor.fetchone() == ("public",)

    with schema.Schema.create(schema_name="test"):
        inner()
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            cursor.fetchone() == ("test, public",)


def test_schema_exists(db):
    assert utils.schema_exists("public")
    assert utils.schema_exists("www")
    assert utils.schema_exists("blog")
    assert not utils.schema_exists("default")


def test_dynamic_models_exist(tenants_settings, db):
    if "default" in tenants_settings:
        assert utils.dynamic_models_exist()
    else:
        assert not utils.dynamic_models_exist()

    utils.drop_schema("public")

    assert not utils.dynamic_models_exist()


def test_create_drop_schema(db):
    assert not utils.create_schema("public", check_if_exists=True)  # Schema existed already
    assert utils.schema_exists("public")  # Schema exists
    assert utils.drop_schema("public")  # Schema was dropped
    assert not utils.drop_schema("public")  # Schema no longer exists
    assert not utils.schema_exists("public")  # Schema doesn't exist
    assert utils.create_schema("public", sync_schema=False)  # Schema was created
    assert utils.schema_exists("public")  # Schema exists


def test_clone_schema(db):
    utils._create_clone_schema_function()

    assert not utils.schema_exists("sample2")  # Schema doesn't exist previously

    utils.clone_schema("sample", "sample2", dry_run=True)  # Dry run

    assert not utils.schema_exists("sample2")  # Schema won't exist, dry run

    utils.clone_schema("sample", "sample2")  # Real run, schema was cloned

    assert utils.schema_exists("sample2")  # Schema exists

    with pytest.raises(DatabaseError):
        utils.clone_schema("sample", "sample2")  # Schema already exists, error

    assert utils.schema_exists("sample2")  # Schema still exists


def test_create_or_clone_schema(db):
    assert not utils.create_or_clone_schema("sample")  # Schema existed


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", ""),
        ("www", "www"),
        ("www.", ""),
        ("www.test.com", "test.com"),
        ("www.test.com/complex/path", "test.com/complex/path"),
        ("1www.test.com", "1www.test.com"),
    ],
)
def test_remove_www(path, expected):
    actual = utils.remove_www(path)

    assert actual == expected
