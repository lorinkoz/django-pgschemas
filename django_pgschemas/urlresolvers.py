import re
import sys

from django.conf import settings
from django.urls import URLResolver

from .schema import SchemaDescriptor, get_current_schema


class TenantPrefixPattern:
    converters = {}

    @property
    def tenant_prefix(self):
        current_schema = get_current_schema()
        return f"{current_schema.folder}/" if current_schema.folder else "/"

    @property
    def regex(self):
        # This is only used by reverse() and cached in _reverse_dict.
        return re.compile(self.tenant_prefix)

    def match(self, path):
        tenant_prefix = self.tenant_prefix
        if path.startswith(tenant_prefix):
            return path[len(tenant_prefix) :], (), {}
        return None

    def check(self):
        return []

    def describe(self):
        return f"'{self}'"

    def __str__(self):
        return self.tenant_prefix


def tenant_patterns(*urls):
    """
    Add the tenant prefix to every URL pattern within this function.
    This may only be used in the root URLconf, not in an included URLconf.
    """
    return [URLResolver(TenantPrefixPattern(), list(urls))]


def get_dynamic_tenant_prefixed_urlconf(urlconf, dynamic_path):
    """
    Generates a new URLConf module with all patterns prefixed with tenant.
    """
    from types import ModuleType

    from django.utils.module_loading import import_string

    class LazyURLConfModule(ModuleType):
        def __getattr__(self, attr):
            imported = import_string(f"{urlconf}.{attr}")
            if attr == "urlpatterns":
                return tenant_patterns(*imported)
            return imported

    return LazyURLConfModule(dynamic_path)


def get_urlconf_from_schema(schema):
    """
    Returns the proper URLConf depending on the schema.
    The schema must come with ``domain_url`` and ``folder`` members set.
    """
    assert isinstance(schema, SchemaDescriptor)

    if not schema.domain_url:
        return None

    # Checking for static tenants
    if not schema.is_dynamic:
        for schema_name, data in settings.TENANTS.items():
            if schema_name in ["public", "default"]:
                continue
            if schema.domain_url in data["DOMAINS"]:
                return data["URLCONF"]
            if schema.domain_url in data.get("FALLBACK_DOMAINS", []):
                return data["URLCONF"]
        return None

    # Checking for dynamic tenants
    urlconf = settings.TENANTS["default"]["URLCONF"]
    if schema.folder:
        dynamic_path = urlconf + "_dynamically_tenant_prefixed"
        if not sys.modules.get(dynamic_path):
            sys.modules[dynamic_path] = get_dynamic_tenant_prefixed_urlconf(urlconf, dynamic_path)
        urlconf = dynamic_path

    return urlconf
