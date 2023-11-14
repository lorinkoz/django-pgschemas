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


def get_pathname_function() -> Callable | None:
    return getattr(settings, "PGSCHEMAS_PATHNAME_FUNCTION", None)


def get_base_backend_module(submodule: str | None = None) -> ModuleType:
    module = DEFAULT_BACKEND
    if submodule:
        module += f".{submodule}"
    return import_module(module)


def get_original_backend_module(submodule: str | None = None) -> ModuleType:
    module = get_original_backend()
    if submodule:
        module += f".{submodule}"
    return import_module(module)
