from functools import partial
from importlib import import_module
from types import ModuleType
from typing import Callable

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

DEFAULT_BACKEND = "django.db.backends.postgresql"


def get_tenant_db_alias() -> str:
    return getattr(settings, "PGSCHEMAS_TENANT_DB_ALIAS", DEFAULT_DB_ALIAS)


def get_limit_set_calls() -> bool:
    return getattr(settings, "PGSCHEMAS_LIMIT_SET_CALLS", False)


def get_original_backend() -> str:
    return getattr(settings, "PGSCHEMAS_ORIGINAL_BACKEND", DEFAULT_BACKEND)


def get_extra_search_paths() -> list[str]:
    return getattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS", [])


def get_tenant_session_key() -> str:
    return getattr(settings, "PGSCHEMAS_TENANT_SESSION_KEY", "tenant")


def get_tenant_header() -> str:
    return getattr(settings, "PGSCHEMAS_TENANT_HEADER", "tenant")


def get_parallel_max_workers() -> int | None:
    if hasattr(settings, "PGSCHEMAS_PARALLEL_MAX_THREADS"):
        return getattr(settings, "PGSCHEMAS_PARALLEL_MAX_THREADS")
    # Backwards compatibility with the old setting name.
    return getattr(settings, "PGSCHEMAS_PARALLEL_MAX_PROCESSES", None)


def get_pathname_function() -> Callable | None:
    return getattr(settings, "PGSCHEMAS_PATHNAME_FUNCTION", None)


def import_backend_module(
    backend: str | Callable[[], str],
    submodule: str | None = None,
) -> ModuleType:
    # Django 6.1+: postgresql.introspection imports psycopg_version from
    # postgresql.base, which imports postgresql.introspection. Importing
    # introspection first leaves base half-initialized and raises ImportError.
    # Django itself never hits this because base is always imported first.
    if callable(backend):
        backend = backend()
    if submodule and submodule != "base":
        import_module(f"{backend}.base")
    module = backend if not submodule else f"{backend}.{submodule}"
    return import_module(module)


get_base_backend_module = partial(import_backend_module, DEFAULT_BACKEND)
get_original_backend_module = partial(import_backend_module, get_original_backend)
