import re

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, transaction, ProgrammingError, DEFAULT_DB_ALIAS


def get_tenant_model():
    "Returns the tenant model."
    return apps.get_model(settings.TENANTS["public"]["TENANT_MODEL"])


def get_domain_model():
    "Returns the domain model."
    return apps.get_model(settings.TENANTS["public"]["DOMAIN_MODEL"])


def get_tenant_database_alias():
    return getattr(settings, "PGSCHEMAS_TENANT_DB_ALIAS", DEFAULT_DB_ALIAS)


def get_limit_set_calls():
    return getattr(settings, "PGSCHEMAS_LIMIT_SET_CALLS", False)


def get_clone_reference():
    return settings.TENANTS["default"].get("CLONE_REFERENCE", None)


def is_valid_identifier(identifier):
    "Checks the validity of identifier."
    SQL_IDENTIFIER_RE = re.compile(r"^[_a-zA-Z][_a-zA-Z0-9]{,62}$")
    return bool(SQL_IDENTIFIER_RE.match(identifier))


def is_valid_schema_name(name):
    "Checks the validity of a schema name."
    SQL_SCHEMA_NAME_RESERVED_RE = re.compile(r"^pg_", re.IGNORECASE)
    return is_valid_identifier(name) and not SQL_SCHEMA_NAME_RESERVED_RE.match(name)


def check_schema_name(name):
    """
    Checks schema name and raises ``ValidationError`` if ``name`` is not a
    valid identifier.
    """
    if not is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")


def remove_www(hostname):
    """
    Removes ``www``. from the beginning of the address. Only for
    routing purposes. ``www.test.com/login/`` and ``test.com/login/`` should
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
    from django.core import mail

    return hasattr(mail, "outbox")


def run_in_public_schema(func):
    "Decorator that makes decorated function to be run in the public schema."

    def wrapper(*args, **kwargs):
        from .schema import SchemaDescriptor

        with SchemaDescriptor.create(schema_name="public"):
            return func(*args, **kwargs)

    return wrapper


def schema_exists(schema_name):
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
def dynamic_models_exist():
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
def create_schema(schema_name, check_if_exists=False, sync_schema=True, verbosity=1):
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
def drop_schema(schema_name, check_if_exists=True, verbosity=1):
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


# Postgres' `clone_schema` adapted to work with schema names containing
# capital letters or `-`
# Source: IdanDavidi, https://stackoverflow.com/a/48732283/6412017
CLONE_SCHEMA_FUNCTION = """
-- Function: clone_schema(text, text, bool)

-- DROP FUNCTION clone_schema(text, text, bool);

CREATE OR REPLACE FUNCTION clone_schema(
    source_schema text,
    dest_schema text,
    include_recs boolean)
  RETURNS void AS
$BODY$

--  This function will clone all sequences, tables, data, views & functions from any existing schema to a new one
-- SAMPLE CALL:
-- SELECT clone_schema('public', 'new_schema', TRUE);

DECLARE
  record           record;
  src_oid          oid;
  tbl_oid          oid;
  func_oid         oid;
  object           text;
  buffer           text;
  srctbl           text;
  default_         text;
  column_          text;
  qry              text;
  dest_qry         text;
  v_def            text;
  seqval           bigint;
  sq_last_value    bigint;
  sq_max_value     bigint;
  sq_start_value   bigint;
  sq_increment_by  bigint;
  sq_min_value     bigint;
  sq_cache_value   bigint;
  sq_log_cnt       bigint;
  sq_is_called     boolean;
  sq_is_cycled     boolean;
  sq_cycled        char(10);

BEGIN

-- Check that source_schema exists
  SELECT oid INTO src_oid
    FROM pg_namespace
   WHERE nspname = source_schema;
  IF NOT FOUND
    THEN
    RAISE EXCEPTION 'Source schema ''%'' does not exist.', source_schema;
    RETURN ;
  END IF;

  -- Check that dest_schema does not yet exist
  PERFORM nspname
    FROM pg_namespace
   WHERE nspname = dest_schema;
  IF FOUND
    THEN
    RAISE EXCEPTION 'Destination schema ''%'' already exists.', dest_schema;
    RETURN ;
  END IF;

  EXECUTE 'CREATE SCHEMA "' || dest_schema || '"';

  -- Create sequences
FOR record IN
    SELECT *
      FROM information_schema.sequences
     WHERE sequence_schema = source_schema
  LOOP
    object := record.sequence_name::text;
    sq_max_value := record.maximum_value;
    sq_start_value := record.start_value;
    sq_increment_by := record.increment;
    sq_min_value := record.minimum_value;
    sq_is_cycled := record.cycle_option;

    EXECUTE 'CREATE SEQUENCE "' || dest_schema || '".' || quote_ident(object);

    EXECUTE 'SELECT last_value, log_cnt, is_called
            FROM "' || source_schema || '".' || quote_ident(object) || ';'
            INTO sq_last_value, sq_log_cnt, sq_is_called;

    IF sq_is_cycled
      THEN
        sq_cycled := 'CYCLE';
    ELSE
        sq_cycled := 'NO CYCLE';
    END IF;

    EXECUTE 'ALTER SEQUENCE "'   || dest_schema || '".' || quote_ident(object)
            || ' INCREMENT BY ' || sq_increment_by
            || ' MINVALUE '     || sq_min_value
            || ' MAXVALUE '     || sq_max_value
            || ' START WITH '   || sq_start_value
            || ' RESTART '      || sq_min_value
            || sq_cycled || ' ;' ;

    buffer := '"' || dest_schema || '".' || quote_ident(object);
    IF include_recs
        THEN
            EXECUTE 'SELECT setval( ''' || buffer || ''', ' || sq_last_value || ', ' || sq_is_called || ');' ;
    ELSE
            EXECUTE 'SELECT setval( ''' || buffer || ''', ' || sq_start_value || ', ' || sq_is_called || ');' ;
    END IF;

  END LOOP;

-- Create tables
  FOR object IN
    SELECT TABLE_NAME::text
      FROM information_schema.tables
     WHERE table_schema = source_schema
       AND table_type = 'BASE TABLE'

  LOOP
    buffer := '"' || dest_schema || '".' || quote_ident(object);
    EXECUTE 'CREATE TABLE ' || buffer || ' (LIKE "' || source_schema || '".' || quote_ident(object)
        || ' INCLUDING ALL)';

    IF include_recs
      THEN
      -- Insert records from source table
      EXECUTE 'INSERT INTO ' || buffer || ' SELECT * FROM "' || source_schema || '".' || quote_ident(object) || ';';
    END IF;

    FOR column_, default_ IN
      SELECT column_name::text, column_default::text
        FROM information_schema.COLUMNS
       WHERE table_schema = dest_schema
         AND TABLE_NAME = object
         AND column_default LIKE 'nextval(%' || source_schema || '.%::regclass)'
    LOOP
      EXECUTE 'ALTER TABLE ' || buffer || ' ALTER COLUMN ' || column_ || ' SET DEFAULT '
            || replace(default_, source_schema || '.', dest_schema || '.');
    END LOOP;

  END LOOP;

--  add FK constraint
  FOR qry IN
    SELECT 'ALTER TABLE "' || dest_schema || '".' || quote_ident(rn.relname)
                          || ' ADD CONSTRAINT ' || quote_ident(ct.conname) || ' ' || pg_get_constraintdef(ct.oid) || ';'
      FROM pg_constraint ct
      JOIN pg_class rn ON rn.oid = ct.conrelid
     WHERE connamespace = src_oid
       AND rn.relkind = 'r'
       AND ct.contype = 'f'

    LOOP
      EXECUTE replace(qry, source_schema || '.', dest_schema || '.');

    END LOOP;


-- Create views
  FOR object IN
    SELECT table_name::text,
           view_definition
      FROM information_schema.views
     WHERE table_schema = source_schema

  LOOP
    buffer := '"' || dest_schema || '".' || quote_ident(object);
    SELECT view_definition INTO v_def
      FROM information_schema.views
     WHERE table_schema = source_schema
       AND table_name = quote_ident(object);

    EXECUTE 'CREATE OR REPLACE VIEW ' || buffer || ' AS ' || v_def || ';' ;

  END LOOP;

-- Create functions
  FOR func_oid IN
    SELECT oid
      FROM pg_proc
     WHERE pronamespace = src_oid

  LOOP
    SELECT pg_get_functiondef(func_oid) INTO qry;
    SELECT replace(qry, source_schema || '.', dest_schema || '.') INTO dest_qry;
    EXECUTE dest_qry;

  END LOOP;

  RETURN;

END;

$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION clone_schema(text, text, boolean)
  OWNER TO {user};
""".format(
    user=settings.DATABASES["default"].get("USER", None) or "postgres"
)


class DryRunException(Exception):
    pass


def _create_clone_schema_function():
    """
    Creates a postgres function `clone_schema` that copies a schema and its
    contents. Will replace any existing `clone_schema` functions owned by the
    `postgres` superuser.
    """
    cursor = connection.cursor()
    cursor.execute(CLONE_SCHEMA_FUNCTION)
    cursor.close()


@run_in_public_schema
def clone_schema(base_schema_name, new_schema_name, dry_run=False):
    """
    Creates a new schema ``new_schema_name`` as a clone of an existing schema
    ``base_schema_name``.
    """
    check_schema_name(new_schema_name)
    cursor = connection.cursor()

    # check if the clone_schema function already exists in the db
    try:
        cursor.execute("SELECT 'clone_schema'::regproc")
    except ProgrammingError:  # pragma: no cover
        _create_clone_schema_function()
        transaction.commit()

    try:
        with transaction.atomic():
            sql = "SELECT clone_schema(%(base_schema)s, %(new_schema)s, TRUE)"
            cursor.execute(sql, {"base_schema": base_schema_name, "new_schema": new_schema_name})
            cursor.close()
            if dry_run:
                raise DryRunException
    except DryRunException:
        cursor.close()


def create_or_clone_schema(schema_name, sync_schema=True, verbosity=1):
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
