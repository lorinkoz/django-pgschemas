import re

from django.conf import settings
from django.db import connection
from django.http import Http404
from django.urls import set_urlconf, clear_url_caches

from .schema import SchemaDescriptor
from .urlresolvers import get_urlconf_from_schema
from .utils import remove_www, get_domain_model


class TenantMiddleware:
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper static/dynamic schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data.
    """

    TENANT_NOT_FOUND_EXCEPTION = Http404

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hostname = remove_www(request.get_host().split(":")[0])
        connection.set_schema_to_public()

        tenant = None

        # Checking for static tenants
        for schema, data in settings.TENANTS.items():
            if schema in ["public", "default"]:
                continue
            if hostname in data["DOMAINS"]:
                tenant = SchemaDescriptor.create(schema_name=schema, domain_url=hostname)
                break

        # Checking for dynamic tenants
        else:
            DomainModel = get_domain_model()
            prefix = request.path.split("/")[1]
            try:
                domain = DomainModel.objects.select_related("tenant").get(domain=hostname, folder=prefix)
            except DomainModel.DoesNotExist:
                try:
                    domain = DomainModel.objects.select_related("tenant").get(domain=hostname, folder="")
                except DomainModel.DoesNotExist:
                    domain = None
            if domain:
                tenant = domain.tenant
                tenant.domain_url = hostname
                tenant.folder = None
                request.strip_tenant_from_path = lambda x: x
                if prefix and domain.folder == prefix:
                    tenant.folder = prefix
                    request.strip_tenant_from_path = lambda x: re.sub(r"^/{}/".format(prefix), "/", x)
                    clear_url_caches()  # Required to remove previous tenant prefix from cache (#8)

        # Checking fallback domains
        if not tenant:
            for schema, data in settings.TENANTS.items():
                if schema in ["public", "default"]:
                    continue
                if hostname in data.get("FALLBACK_DOMAINS", []):
                    tenant = SchemaDescriptor.create(schema_name=schema, domain_url=hostname)
                    break

        # No tenant found from domain / folder
        if not tenant:
            raise self.TENANT_NOT_FOUND_EXCEPTION("No tenant for hostname '%s'" % hostname)

        request.tenant = tenant
        urlconf = get_urlconf_from_schema(tenant)
        request.urlconf = urlconf
        set_urlconf(urlconf)
        connection.set_schema(tenant)
        return self.get_response(request)
