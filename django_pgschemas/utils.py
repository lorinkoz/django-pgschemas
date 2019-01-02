import re

from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connections, DEFAULT_DB_ALIAS


def get_tenant_model():
    return apps.get_model(settings.TENANTS["public"]["TENANT_MODEL"])


def get_domain_model():
    return apps.get_model(settings.TENANTS["public"]["DOMAIN_MODEL"])


def get_tenant_database_alias():
    return getattr(settings, "PGSCHEMAS_TENANT_DB_ALIAS", DEFAULT_DB_ALIAS)


def get_limit_set_calls():
    return getattr(settings, "PGSCHEMAS_LIMIT_SET_CALLS", False)


def get_creation_fakes_migrations():
    return getattr(settings, "PGSCHEMAS_CREATION_FAKES_MIGRATIONS", False)


def is_valid_identifier(identifier):
    SQL_IDENTIFIER_RE = re.compile(r"^[_a-zA-Z][_a-zA-Z0-9]{,62}$")
    return bool(SQL_IDENTIFIER_RE.match(identifier))


def is_valid_schema_name(name):
    SQL_SCHEMA_NAME_RESERVED_RE = re.compile(r"^pg_", re.IGNORECASE)
    return is_valid_identifier(name) and not SQL_SCHEMA_NAME_RESERVED_RE.match(name)


def check_identifier(identifier):
    if not is_valid_identifier(identifier):
        raise ValidationError("Invalid string used for the identifier.")


def check_schema_name(name):
    if not is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")


def remove_www(hostname):
    """
    Removes www. from the beginning of the address. Only for
    routing purposes. www.test.com/login/ and test.com/login/ should
    find the same tenant.
    """
    if hostname.startswith("www."):
        return hostname[4:]
    return hostname


def django_is_in_test_mode():
    """
    I know this is very ugly! I'm looking for more elegant solutions.
    See: http://stackoverflow.com/questions/6957016/detect-django-testing-mode
    """
    return hasattr(mail, "outbox")


def schema_exists(schema_name):
    connection = connections[get_tenant_database_alias()]
    cursor = connection.cursor()
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE LOWER(nspname) = LOWER(%s))", (schema_name,)
    )
    row = cursor.fetchone()
    if row:
        exists = row[0]
    else:
        exists = False
    cursor.close()
    return exists


def create_schema(schema_name, check_if_exists=False, sync_schema=True, verbosity=1):
    """
    Creates the schema 'schema_name'. Optionally checks if the schema already
    exists before creating it. Returns true if the schema was created, false otherwise.
    """
    check_schema_name(schema_name)
    if check_if_exists and schema_exists(schema_name):
        return False
    connection = connections[get_tenant_database_alias()]
    cursor = connection.cursor()
    cursor.execute("CREATE SCHEMA %s" % schema_name)
    if sync_schema:
        call_command("migrate_schemas", schema=schema_name, verbosity=verbosity)
    return True


def drop_schema(schema_name, check_if_exists=True, verbosity=1):
    if check_if_exists and not schema_exists(schema_name):
        return False
    connection = connections[get_tenant_database_alias()]
    cursor = connection.cursor()
    cursor.execute("DROP SCHEMA %s CASCADE" % schema_name)
    return True
