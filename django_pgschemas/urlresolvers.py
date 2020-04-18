import re
import sys
from importlib.util import find_spec, module_from_spec

from django.conf import settings
from django.db import connection
from django.urls import URLResolver
from django.utils.module_loading import import_string

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


def get_urlconf_from_schema(schema):
    """
    Returns the proper URLConf depending on the schema.
    The schema must come with domain_url and folder members set.
    If the schema comes with subfolder routing, a new module will be created
    on the fly.
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
                if "URLCONF" in data:
                    return data["URLCONF"]
                return None
        return None

    # Checking for dynamic tenants
    urlconf = settings.TENANTS["default"]["URLCONF"]
    if schema.folder:
        dynamic_path = settings.TENANTS["default"]["URLCONF"] + "_dynamically_tenant_prefixed"
        if not sys.modules.get(dynamic_path):
            spec = find_spec(settings.TENANTS["default"]["URLCONF"])
            prefixed_url_module = module_from_spec(spec)
            spec.loader.exec_module(prefixed_url_module)
            prefixed_url_module.urlpatterns = tenant_patterns(
                *import_string(settings.TENANTS["default"]["URLCONF"] + ".urlpatterns")
            )
            sys.modules[dynamic_path] = prefixed_url_module
            del spec
        urlconf = dynamic_path

    return urlconf
