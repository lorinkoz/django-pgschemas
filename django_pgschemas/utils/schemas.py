import os
import re

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import ProgrammingError, connection, transaction

from .other import django_is_in_test_mode
from .settings import get_clone_reference, get_domain_model, get_tenant_model


def is_valid_identifier(identifier: str) -> bool:
    "Checks the validity of identifier."
    SQL_IDENTIFIER_RE = re.compile(r"^[_a-zA-Z][_a-zA-Z0-9]{,62}$")
    return bool(SQL_IDENTIFIER_RE.match(identifier))


def is_valid_schema_name(name: str) -> bool:
    "Checks the validity of a schema name."
    SQL_SCHEMA_NAME_RESERVED_RE = re.compile(r"^pg_", re.IGNORECASE)
    return is_valid_identifier(name) and not SQL_SCHEMA_NAME_RESERVED_RE.match(name)


def check_schema_name(name: str):
    """
    Checks schema name and raises ``ValidationError`` if ``name`` is not a
    valid identifier.
    """
    if not is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")


def run_in_public_schema(func):
    "Decorator that makes decorated function to be run in the public schema."

    def wrapper(*args, **kwargs):
        from ..schema import Schema

        with Schema.create(schema_name="public"):
            return func(*args, **kwargs)

    return wrapper


def schema_exists(schema_name: str) -> bool:
    "Checks if a schema exists in database."
    sql = """
    SELECT EXISTS(
        SELECT 1
        FROM pg_catalog.pg_namespace
        WHERE LOWER(nspname) = LOWER(%s)
    )
    """
    cursor = connection.cursor()
    cursor.execute(sql, (schema_name,))
    row = cursor.fetchone()
    if row:
        exists = row[0]
    else:  # pragma: no cover
        exists = False
    cursor.close()
    return exists


@run_in_public_schema
def dynamic_models_exist() -> bool:
    "Checks if tenant model and domain model have been synced."
    sql = """
    SELECT count(*)
    FROM   information_schema.tables
    WHERE  table_schema = 'public'
    AND    table_name in ('%s', '%s');
    """
    cursor = connection.cursor()
    cursor.execute(sql % (get_tenant_model()._meta.db_table, get_domain_model()._meta.db_table))
    value = cursor.fetchone() == (2,)
    cursor.close()
    return value


@run_in_public_schema
def create_schema(
    schema_name: str,
    check_if_exists: bool = False,
    sync_schema: bool = True,
    verbosity: int = 1,
) -> bool:
    """
    Creates the schema ``schema_name``. Optionally checks if the schema already
    exists before creating it. Returns ``True`` if the schema was created,
    ``False`` otherwise.
    """
    check_schema_name(schema_name)
    if check_if_exists and schema_exists(schema_name):
        return False
    cursor = connection.cursor()
    cursor.execute("CREATE SCHEMA %s" % schema_name)
    cursor.close()
    if sync_schema:
        call_command("migrateschema", schemas=[schema_name], verbosity=verbosity)
    return True


@run_in_public_schema
def drop_schema(schema_name: str, check_if_exists: bool = True, verbosity: int = 1) -> bool:
    """
    Drops the schema. Optionally checks if the schema already exists before
    dropping it.
    """
    if check_if_exists and not schema_exists(schema_name):
        return False
    cursor = connection.cursor()
    cursor.execute("DROP SCHEMA %s CASCADE" % schema_name)
    cursor.close()
    return True


class DryRunException(Exception):
    pass


def create_clone_schema_function():
    """
    Creates a postgres function `clone_schema` that copies a schema and its
    contents. Will replace any existing `clone_schema` functions owned by the
    `postgres` superuser.
    """
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clone_schema.sql")) as f:
        CLONE_SCHEMA_FUNCTION = (
            f.read()
            .replace("RAISE NOTICE ' source schema", "RAISE EXCEPTION ' source schema")
            .replace("RAISE NOTICE ' dest schema", "RAISE EXCEPTION ' dest schema")
        )

    cursor = connection.cursor()
    cursor.execute(CLONE_SCHEMA_FUNCTION)
    cursor.close()


@run_in_public_schema
def clone_schema(base_schema_name: str, new_schema_name: str, dry_run: bool = False):
    """
    Creates a new schema ``new_schema_name`` as a clone of an existing schema
    ``base_schema_name``.
    """
    check_schema_name(new_schema_name)
    cursor = connection.cursor()

    # check if the clone_schema function already exists in the db
    try:
        cursor.execute("SELECT 'public.clone_schema(text, text, public.cloneparms[])'::regprocedure")
    except ProgrammingError:  # pragma: no cover
        create_clone_schema_function()
        transaction.commit()

    try:
        with transaction.atomic():
            cursor.callproc("clone_schema", [base_schema_name, new_schema_name, "DATA"])
            cursor.close()
            if dry_run:
                raise DryRunException
    except DryRunException:
        cursor.close()


def create_or_clone_schema(schema_name: str, sync_schema: bool = True, verbosity: int = 1) -> bool:
    """
    Creates the schema ``schema_name``. Optionally checks if the schema already
    exists before creating it. Returns ``True`` if the schema was created,
    ``False`` otherwise.
    """
    check_schema_name(schema_name)
    if schema_exists(schema_name):
        return False
    clone_reference = get_clone_reference()
    if clone_reference and schema_exists(clone_reference) and not django_is_in_test_mode():  # pragma: no cover
        clone_schema(clone_reference, schema_name)
        return True
    return create_schema(schema_name, sync_schema=sync_schema, verbosity=verbosity)
