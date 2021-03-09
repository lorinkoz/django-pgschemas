from importlib import import_module

import psycopg2
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import DatabaseError

from ..schema import get_current_schema, set_schema_to_public
from ..utils import check_schema_name, get_limit_set_calls
from .introspection import DatabaseSchemaIntrospection

ORIGINAL_BACKEND = getattr(settings, "PGSCHEMAS_ORIGINAL_BACKEND", "django.db.backends.postgresql")
EXTRA_SEARCH_PATHS = getattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS", [])

original_backend = import_module(ORIGINAL_BACKEND + ".base")
IntegrityError = psycopg2.IntegrityError


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to manipulate the search_path using set_schema
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.introspection = DatabaseSchemaIntrospection(self)
        set_schema_to_public()

    def close(self):
        current_schema = get_current_schema()
        if current_schema:
            current_schema.ready = False
        super().close()

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

        current_schema = get_current_schema()

        # optionally limit the number of executions - under load, the execution
        # of `set search_path` can be quite time consuming
        if (not get_limit_set_calls()) or not current_schema.ready:
            # Actual search_path modification for the cursor. Database will
            # search schemas from left to right when looking for the object
            # (table, index, sequence, etc.).
            if not current_schema:
                raise ImproperlyConfigured("Database schema not set. Did you forget to call set_schema()?")
            check_schema_name(current_schema.schema_name)
            search_paths = []

            if current_schema.schema_name == "public":
                search_paths = ["public"]
            else:
                search_paths = [current_schema.schema_name, "public"]
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
                current_schema.ready = False
            else:
                current_schema.ready = True
            if name:
                cursor_for_search_path.close()
        return cursor
