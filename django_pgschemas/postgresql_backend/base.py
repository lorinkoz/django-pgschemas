import psycopg2
from django.db.utils import DatabaseError

from ..schema import get_current_schema, get_default_schema
from ..utils import check_schema_name, get_limit_set_calls
from .introspection import DatabaseSchemaIntrospection
from .settings import EXTRA_SEARCH_PATHS, original_backend

IntegrityError = psycopg2.IntegrityError


def get_search_path(schema=None):
    if schema is None:
        schema = get_default_schema()

    search_path = ["public"] if schema.schema_name == "public" else [schema.schema_name, "public"]
    search_path.extend(EXTRA_SEARCH_PATHS)

    for part in search_path:
        check_schema_name(part)

    return ", ".join(search_path)


class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        self._search_path = None
        super().__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.introspection = DatabaseSchemaIntrospection(self)

    def close(self):
        self._search_path = None
        super().close()

    def _cursor(self, name=None):
        if name:
            # Only supported and required by Django 1.11 (server-side cursor)
            cursor = super()._cursor(name=name)
        else:
            cursor = super()._cursor()

        search_path_for_current_schema = get_search_path(get_current_schema())

        # optionally limit the number of executions - under load, the execution
        # of `set search_path` can be quite time consuming
        if (not get_limit_set_calls()) or (self._search_path != search_path_for_current_schema):
            # Actual search_path modification for the cursor. Database will
            # search schemas from left to right when looking for the object
            # (table, index, sequence, etc.).

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
                cursor_for_search_path.execute(f"SET search_path = {search_path_for_current_schema}")
            except (DatabaseError, psycopg2.InternalError):
                self._search_path = None
            else:
                self._search_path = search_path_for_current_schema
            if name:
                cursor_for_search_path.close()
        return cursor
