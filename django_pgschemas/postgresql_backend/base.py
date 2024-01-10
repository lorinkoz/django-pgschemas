from django.core.exceptions import ImproperlyConfigured
from django.db.utils import DatabaseError

from ..schema import get_current_schema, get_default_schema
from ..utils import check_schema_name, get_limit_set_calls
from .introspection import DatabaseSchemaIntrospection
from .settings import EXTRA_SEARCH_PATHS, original_backend

try:
    try:
        import psycopg as _psycopg
    except ImportError:
        import psycopg2 as _psycopg
except ImportError:
    raise ImproperlyConfigured("Error loading psycopg2 or psycopg module")

IntegrityError = _psycopg.IntegrityError


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
        self._setting_search_path = False
        super().__init__(*args, **kwargs)

        # Patched version of DatabaseIntrospection that only returns the table list for the currently selected schema
        self.introspection = DatabaseSchemaIntrospection(self)

    def close(self):
        self._search_path = None
        self._setting_search_path = False
        super().close()

    def _handle_search_path(self, cursor=None):
        search_path_for_current_schema = get_search_path(get_current_schema())

        skip = self._setting_search_path or (
            self._search_path == search_path_for_current_schema and get_limit_set_calls()
        )

        if not skip:
            self._setting_search_path = True
            cursor_for_search_path = self.connection.cursor() if cursor is None else cursor

            try:
                cursor_for_search_path.execute(
                    f"SET search_path = {search_path_for_current_schema}"
                )
            except (DatabaseError, _psycopg.InternalError):
                self._search_path = None
            else:
                self._search_path = search_path_for_current_schema
            finally:
                self._setting_search_path = False

            if cursor is None:
                cursor_for_search_path.close()

    def _cursor(self, name=None):
        cursor = super()._cursor(name=name)

        cursor_for_search_path = cursor if name is None else None  # Named cursors cannot be reused
        self._handle_search_path(cursor_for_search_path)

        return cursor
