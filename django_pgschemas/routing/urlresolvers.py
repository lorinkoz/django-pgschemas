import re
import sys
from types import ModuleType
from typing import Any, Literal

from django.conf import settings
from django.urls import URLResolver

from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.schema import Schema, get_current_schema

DYNAMIC_URLCONF_SUFFIX = "_dynamically_tenant_prefixed"


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


def get_dynamic_tenant_prefixed_urlconf(urlconf: str, dynamic_path: str) -> ModuleType:
    """
    Generates a new urlconf module with all patterns prefixed with tenant.
    """

    class LazyURLConfModule(ModuleType):
        def __getattr__(self, attr: str) -> Any:
            if attr == "urlpatterns":
                return [URLResolver(TenantPrefixPattern(), urlconf)]
            return self.__getattribute__(attr)

    return LazyURLConfModule(dynamic_path)


def _get_urlconf_from_schema(
    schema: Schema, config_key: Literal["URLCONF", "WS_URLCONF"]
) -> str | None:
    match schema.routing:
        case DomainInfo(domain, _):
            # Checking for static tenants
            if not schema.is_dynamic:
                for schema_name, data in settings.TENANTS.items():
                    if schema_name in ["public", "default"]:
                        continue
                    if domain in data.get("DOMAINS", []):
                        return data.get(config_key)
                    if domain in data.get("FALLBACK_DOMAINS", []):
                        return data.get(config_key)
                return None

            # Checking for dynamic tenants
            urlconf = settings.TENANTS.get("default", {}).get(config_key)
            if urlconf is not None and schema.routing.folder:
                dynamic_path = urlconf + DYNAMIC_URLCONF_SUFFIX
                if not sys.modules.get(dynamic_path):
                    sys.modules[dynamic_path] = get_dynamic_tenant_prefixed_urlconf(
                        urlconf, dynamic_path
                    )
                urlconf = dynamic_path

            return urlconf

        case SessionInfo(reference):
            # Checking for static tenants
            if not schema.is_dynamic:
                for schema_name, data in settings.TENANTS.items():
                    if schema_name in ["public", "default"]:
                        continue
                    if reference == data.get("SESSION_KEY"):
                        return data.get(config_key)
                return None

            # Checking for dynamic tenants
            return settings.TENANTS.get("default", {}).get(config_key)

        case HeadersInfo(reference):
            # Checking for static tenants
            if not schema.is_dynamic:
                for schema_name, data in settings.TENANTS.items():
                    if schema_name in ["public", "default"]:
                        continue
                    if reference == data.get("HEADER"):
                        return data.get(config_key)
                return None

            # Checking for dynamic tenants
            return settings.TENANTS.get("default", {}).get(config_key)

        case _:
            return None


def get_urlconf_from_schema(schema: Schema) -> str | None:
    return _get_urlconf_from_schema(schema, "URLCONF")


def get_ws_urlconf_from_schema(schema: Schema) -> str | None:
    return _get_urlconf_from_schema(schema, "WS_URLCONF")
