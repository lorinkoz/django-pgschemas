from typing import Optional

from django.apps import apps
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Model


def get_tenant_model(require_ready: bool = True) -> Model:
    "Returns the tenant model."
    return apps.get_model(settings.TENANTS["default"]["TENANT_MODEL"], require_ready=require_ready)


def get_domain_model(require_ready: bool = True) -> Model:
    "Returns the domain model."
    return apps.get_model(settings.TENANTS["default"]["DOMAIN_MODEL"], require_ready=require_ready)


def get_tenant_database_alias() -> str:
    return getattr(settings, "PGSCHEMAS_TENANT_DB_ALIAS", DEFAULT_DB_ALIAS)


def get_limit_set_calls() -> bool:
    return getattr(settings, "PGSCHEMAS_LIMIT_SET_CALLS", False)


def get_clone_reference() -> Optional[str]:
    return settings.TENANTS["default"].get("CLONE_REFERENCE", None)
