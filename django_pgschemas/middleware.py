import re

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect
from django.urls import clear_url_caches, set_urlconf
from django.utils.decorators import sync_and_async_middleware

from .schema import SchemaDescriptor, activate, activate_public
from .urlresolvers import get_urlconf_from_schema
from .utils import get_domain_model, remove_www


def strip_tenant_from_path_factory(prefix):
    def strip_tenant_from_path(path):
        return re.sub(r"^/{}/".format(prefix), "/", path)

    return strip_tenant_from_path


@sync_and_async_middleware
def TenantMiddleware(get_response):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper static/dynamic tenant using the request host.
    """

    def logic(request):
        hostname = remove_www(request.get_host().split(":")[0])

        activate_public()
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
            domain = None

            if DomainModel is not None:
                try:
                    domain = DomainModel.objects.select_related("tenant").get(
                        domain=hostname, folder=prefix
                    )
                except DomainModel.DoesNotExist:
                    try:
                        domain = DomainModel.objects.select_related("tenant").get(
                            domain=hostname, folder=""
                        )
                    except DomainModel.DoesNotExist:
                        pass

            if domain is not None:
                tenant = domain.tenant
                tenant.domain_url = hostname
                tenant.folder = None
                request.strip_tenant_from_path = lambda x: x
                if prefix and domain.folder == prefix:
                    tenant.folder = prefix
                    request.strip_tenant_from_path = strip_tenant_from_path_factory(prefix)
                    clear_url_caches()  # Required to remove previous tenant prefix from cache (#8)
                if domain.redirect_to_primary:
                    primary_domain = tenant.domains.get(is_primary=True)
                    path = request.strip_tenant_from_path(request.path)
                    return redirect(primary_domain.absolute_url(path), permanent=True)

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
            raise Http404("No tenant for hostname '%s'" % hostname)

        request.tenant = tenant
        urlconf = get_urlconf_from_schema(tenant)
        request.urlconf = urlconf
        set_urlconf(urlconf)

        activate(tenant)

    if iscoroutinefunction(get_response):
        async_logic = sync_to_async(logic)

        async def middleware(request):
            if response := await async_logic(request):
                return response

            return await get_response(request)

    else:

        def middleware(request):
            if response := logic(request):
                return response

            return get_response(request)

    return middleware
