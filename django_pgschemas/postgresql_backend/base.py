import psycopg2
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import DatabaseError

from ..schema import SchemaDescriptor
from ..utils import check_schema_name, get_limit_set_calls
from .introspection import DatabaseSchemaIntrospection
from .settings import EXTRA_SEARCH_PATHS, original_backend

IntegrityError = psycopg2.IntegrityError


class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        self._schema = None
        self._search_path_set = None
        super().__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.introspection = DatabaseSchemaIntrospection(self)
        self._set_schema_to_public()

    def close(self):
        self._search_path_set = False
        super().close()

    def _set_schema(self, schema_descriptor):
        assert isinstance(
            schema_descriptor, SchemaDescriptor
        ), "'set_schema' must be called with a SchemaDescriptor descendant"
        self._schema = schema_descriptor
        self._search_path_set = False

    def _set_schema_to_public(self):
        self._set_schema(SchemaDescriptor.create("public"))

    def _get_search_path(self):
        search_path = ["public"] if self._schema.schema_name == "public" else [self._schema.schema_name, "public"]
        search_path.extend(EXTRA_SEARCH_PATHS)
        return search_path

    def _cursor(self, name=None):
        if name:
            # Only supported and required by Django 1.11 (server-side cursor)
            cursor = super()._cursor(name=name)
        else:
            cursor = super()._cursor()

        # optionally limit the number of executions - under load, the execution
        # of `set search_path` can be quite time consuming
        if (not get_limit_set_calls()) or not self._search_path_set:
            # Actual search_path modification for the cursor. Database will
            # search schemas from left to right when looking for the object
            # (table, index, sequence, etc.).
            if not self._schema:
                raise ImproperlyConfigured("Database schema not set. Did you forget to call set_schema()?")

            check_schema_name(self._schema.schema_name)
            search_path = ",".join(self._get_search_path())

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
                cursor_for_search_path.execute(f"SET search_path = {search_path}")
            except (DatabaseError, psycopg2.InternalError):
                self._search_path_set = False
            else:
                self._search_path_set = True
            if name:
                cursor_for_search_path.close()
        return cursor
