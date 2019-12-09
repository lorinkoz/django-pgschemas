from importlib import import_module
import psycopg2

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import DatabaseError

from ..schema import SchemaDescriptor
from ..utils import get_limit_set_calls, check_schema_name
from .introspection import DatabaseSchemaIntrospection

ORIGINAL_BACKEND = getattr(settings, "PGSCHEMAS_ORIGINAL_BACKEND", "django.db.backends.postgresql")
EXTRA_SEARCH_PATHS = getattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS", [])

original_backend = import_module(ORIGINAL_BACKEND + ".base")
IntegrityError = psycopg2.IntegrityError


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to manipulate the search_path using set_schema
    """

    include_public_schema = True

    def __init__(self, *args, **kwargs):
        self.schema = None
        self.search_path_set = None
        super().__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.introspection = DatabaseSchemaIntrospection(self)
        self.set_schema_to_public()

    def close(self):
        self.search_path_set = False
        super().close()

    def set_schema(self, schema_descriptor, include_public=True):
        """
        Main API method to set current database schema,
        but it does not actually modify the db connection.
        """
        assert isinstance(
            schema_descriptor, SchemaDescriptor
        ), "'set_schema' must be called with a SchemaDescriptor descendant"
        self.schema = schema_descriptor
        self.include_public_schema = include_public
        self.search_path_set = False

    def set_schema_to(self, schema_name, domain_url=None, folder=None, include_public=True):
        self.set_schema(SchemaDescriptor.create(schema_name, domain_url, folder), include_public)

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.set_schema_to("public", include_public=False)

    def _cursor(self, name=None):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """
        if name:
            # Only supported and required by Django 1.11 (server-side cursor)
            cursor = super()._cursor(name=name)
        else:
            cursor = super()._cursor()

        # optionally limit the number of executions - under load, the execution
        # of `set search_path` can be quite time consuming
        if (not get_limit_set_calls()) or not self.search_path_set:
            # Actual search_path modification for the cursor. Database will
            # search schemas from left to right when looking for the object
            # (table, index, sequence, etc.).
            if not self.schema:
                raise ImproperlyConfigured("Database schema not set. Did you forget to call set_schema()?")
            check_schema_name(self.schema.schema_name)
            search_paths = []

            if self.schema.schema_name == "public":
                search_paths = ["public"]
            elif self.include_public_schema:
                search_paths = [self.schema.schema_name, "public"]
            else:
                search_paths = [self.schema.schema_name]
            search_paths.extend(EXTRA_SEARCH_PATHS)

            if name:
                # Named cursor can only be used once
                cursor_for_search_path = self.connection.cursor()
            else:
                # Reuse
                cursor_for_search_path = cursor

            # In the event that an error already happened in this transaction and we are going
            # to rollback we should just ignore database error when setting the search_path
            # if the next instruction is not a rollback it will just fail also, so
            # we do not have to worry that it's not the good one
            try:
                cursor_for_search_path.execute("SET search_path = {0}".format(",".join(search_paths)))
            except (DatabaseError, psycopg2.InternalError):
                self.search_path_set = False
            else:
                self.search_path_set = True
            if name:
                cursor_for_search_path.close()
        return cursor
