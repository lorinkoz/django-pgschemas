import re
import sys
from types import ModuleType
from typing import Any

from django.conf import settings
from django.urls import URLResolver

from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.schema import Schema, get_current_schema


class TenantPrefixPattern:
    converters: dict = {}

    @property
    def tenant_prefix(self) -> str:
        current_schema = get_current_schema()
        return (
            f"{current_schema.routing.folder}/"
            if isinstance(current_schema.routing, DomainInfo) and current_schema.routing.folder
            else ""
        )

    @property
    def regex(self) -> re.Pattern:
        # This is only used by reverse() and cached in _reverse_dict.
        return re.compile(self.tenant_prefix)

    def match(self, path: str) -> tuple | None:
        tenant_prefix = self.tenant_prefix
        if path.startswith(tenant_prefix):
            return path[len(tenant_prefix) :], (), {}
        return None

    def check(self) -> list:
        return []

    def describe(self) -> str:
        return f"'{self}'"

    def __str__(self) -> str:
        return self.tenant_prefix


def tenant_patterns(*urls: object) -> list[URLResolver]:
    """
    Add the tenant prefix to every URL pattern within this function.
    This may only be used in the root URLconf, not in an included URLconf.
    """

    return [URLResolver(TenantPrefixPattern(), list(urls))]


def get_dynamic_tenant_prefixed_urlconf(urlconf: str, dynamic_path: str) -> ModuleType:
    """
    Generates a new URLConf module with all patterns prefixed with tenant.
    """

    from django.utils.module_loading import import_string

    class LazyURLConfModule(ModuleType):
        def __getattr__(self, attr: str) -> Any:
            imported = import_string(f"{urlconf}.{attr}")
            if attr == "urlpatterns":
                return tenant_patterns(*imported)
            return imported

    return LazyURLConfModule(dynamic_path)


def _get_urlconf_from_schema(schema: Schema, config_key: str) -> str | None:
    domain_info = schema.routing if isinstance(schema.routing, DomainInfo) else None

    if not domain_info:
        return None

    # Checking for static tenants
    if not schema.is_dynamic:
        for schema_name, data in settings.TENANTS.items():
            if schema_name in ["public", "default"]:
                continue
            if domain_info.domain in data.get("DOMAINS", []):
                return data.get(config_key)
            if domain_info.domain in data.get("FALLBACK_DOMAINS", []):
                return data.get(config_key)
        return None

    # Checking for dynamic tenants
    urlconf = settings.TENANTS["default"][config_key]
    if domain_info.folder:
        dynamic_path = urlconf + "_dynamically_tenant_prefixed"
        if not sys.modules.get(dynamic_path):
            sys.modules[dynamic_path] = get_dynamic_tenant_prefixed_urlconf(urlconf, dynamic_path)
        urlconf = dynamic_path

    return urlconf


def get_urlconf_from_schema(schema: Schema) -> str | None:
    return _get_urlconf_from_schema(schema, "URLCONF")


def get_ws_urlconf_from_schema(schema: Schema) -> str | None:
    return _get_urlconf_from_schema(schema, "WS_URLCONF")
