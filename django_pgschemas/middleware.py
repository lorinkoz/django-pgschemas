import re
import sys
from importlib.util import find_spec, module_from_spec
from types import ModuleType

from django.conf import settings
from django.db import connection
from django.http import Http404
from django.urls import clear_url_caches
from django.utils.module_loading import import_string

from .schema import SchemaDescriptor
from .urlresolvers import tenant_patterns
from .utils import remove_www, get_tenant_model, get_domain_model


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

        # Checking for static tenants
        for schema, data in settings.TENANTS.items():
            if schema in ["public", "default"]:
                continue
            if hostname in data["DOMAINS"]:
                tenant = SchemaDescriptor.create(schema_name=schema, domain_url=hostname)
                request.tenant = tenant
                if "URLCONF" in data:
                    request.urlconf = data["URLCONF"]
                connection.set_schema(request.tenant)
                return self.get_response(request)

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
                    raise self.TENANT_NOT_FOUND_EXCEPTION("No tenant for hostname '%s'" % hostname)
            tenant = domain.tenant
            tenant.domain_url = hostname
            tenant.folder = None
            request.urlconf = settings.TENANTS["default"]["URLCONF"]
            request.strip_tenant_from_path = lambda x: x
            if prefix and domain.folder == prefix:
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
                tenant.folder = prefix
                request.urlconf = dynamic_path
                request.strip_tenant_from_path = lambda x: re.sub(r"^/{}/".format(prefix), "/", x)
                clear_url_caches()  # Required to remove previous tenant prefix from cache (#8)
            request.tenant = tenant
            connection.set_schema(request.tenant)
            return self.get_response(request)
