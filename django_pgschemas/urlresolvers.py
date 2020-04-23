import re
import sys

from django.conf import settings
from django.db import connection
from django.urls import URLResolver

from .utils import get_domain_model
from .schema import SchemaDescriptor


class TenantPrefixPattern:
    converters = {}

    @property
    def tenant_prefix(self):
        DomainModel = get_domain_model()
        try:
            domain = DomainModel.objects.exclude(folder="").get(
                tenant__schema_name=connection.schema.schema_name, domain=connection.schema.domain_url
            )
            return "{}/".format(domain.folder)
        except DomainModel.DoesNotExist:
            return "/"

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
        return "'{}'".format(self)

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

    def get_from_code():
        from types import ModuleType

        DYNAMIC_MODULE_CODE = """
from {urlconf} import *
from {urlconf} import urlpatterns as original_urlpatterns
from django_pgschemas.urlresolvers import tenant_patterns

urlpatterns = tenant_patterns(*original_urlpatterns)
"""
        prefixed_url_module = ModuleType(urlconf)
        exec(DYNAMIC_MODULE_CODE.format(urlconf=urlconf), prefixed_url_module.__dict__)
        return prefixed_url_module

    def get_from_spec():
        from importlib.util import find_spec, module_from_spec
        from django.utils.module_loading import import_string

        spec = find_spec(urlconf)
        prefixed_url_module = module_from_spec(spec)
        spec.loader.exec_module(prefixed_url_module)
        prefixed_url_module.urlpatterns = tenant_patterns(*import_string(urlconf + ".urlpatterns"))
        del spec
        return prefixed_url_module

    def get_from_lazy_module():
        from types import ModuleType

        class LazyURLConfModule(ModuleType):
            def __getattr__(self, attr):
                from django.utils.module_loading import import_string

                if attr == "urlpatterns":
                    return tenant_patterns(*import_string(urlconf + ".urlpatterns"))
                return import_string(urlconf + "." + attr)

        return LazyURLConfModule(dynamic_path)

    # return get_from_code()
    return get_from_spec()
    # return get_from_lazy_module()


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
