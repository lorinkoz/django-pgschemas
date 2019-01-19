import re

from django.db import connection
from django.urls import URLResolver

from .utils import get_domain_model


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
