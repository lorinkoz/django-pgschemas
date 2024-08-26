import re
from typing import Callable, TypeAlias, cast

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import clear_url_caches, set_urlconf
from django.utils.decorators import sync_and_async_middleware

from django_pgschemas.models import TenantModel as TenantModelBase
from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.routing.models import get_primary_domain_for_tenant
from django_pgschemas.routing.urlresolvers import get_urlconf_from_schema
from django_pgschemas.schema import Schema, activate, activate_public
from django_pgschemas.settings import get_tenant_header, get_tenant_session_key
from django_pgschemas.utils import get_domain_model, get_tenant_model, remove_www


def strip_tenant_from_path_factory(prefix: str) -> Callable[[str], str]:
    def strip_tenant_from_path(path: str) -> str:
        return re.sub(r"^/{}/".format(prefix), "/", path)

    return strip_tenant_from_path


ResponseHandler: TypeAlias = Callable[[HttpRequest], HttpResponse]


def route_domain(request: HttpRequest) -> HttpResponse | None:
    hostname = remove_www(request.get_host().split(":")[0])

    activate_public()
    tenant: Schema | None = None

    # Checking for static tenants
    for schema, data in settings.TENANTS.items():
        if schema in ["public", "default"]:
            continue
        if hostname in data.get("DOMAINS", []):
            tenant = Schema.create(
                schema_name=schema,
                routing=DomainInfo(domain=hostname),
            )
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
            tenant = cast(TenantModelBase, domain.tenant)
            tenant.routing = DomainInfo(domain=hostname)
            request.strip_tenant_from_path = lambda x: x

            if prefix and domain.folder == prefix:
                tenant.routing = DomainInfo(domain=hostname, folder=prefix)
                request.strip_tenant_from_path = strip_tenant_from_path_factory(prefix)
                clear_url_caches()  # Required to remove previous tenant prefix from cache (#8)

            if domain.redirect_to_primary:
                primary_domain = get_primary_domain_for_tenant(tenant)
                if primary_domain:
                    path = request.strip_tenant_from_path(request.path)
                    return redirect(primary_domain.absolute_url(path), permanent=True)

    # Checking fallback domains
    if not tenant:
        for schema, data in settings.TENANTS.items():
            if schema in ["public", "default"]:
                continue
            if hostname in data.get("FALLBACK_DOMAINS", []):
                tenant = Schema.create(
                    schema_name=schema,
                    routing=DomainInfo(domain=hostname),
                )
                break

    # No tenant found from domain / folder
    if not tenant:
        raise Http404("No tenant for hostname '%s'" % hostname)

    urlconf = get_urlconf_from_schema(tenant)

    request.tenant = tenant
    request.urlconf = urlconf
    set_urlconf(urlconf)

    activate(tenant)
    return None


def route_session(request: HttpRequest) -> HttpResponse | None:
    tenant_session_key = get_tenant_session_key()

    if not hasattr(request, "session") or not (
        tenant_ref := request.session.get(tenant_session_key)
    ):
        return None

    tenant: Schema | None = None

    # Checking for static tenants
    for schema, data in settings.TENANTS.items():
        if schema in ["public", "default"]:
            continue
        if tenant_ref == schema or tenant_ref == data.get("SESSION_KEY"):
            tenant = Schema.create(schema_name=schema)
            break

    # Checking for dynamic tenants
    else:
        if (TenantModel := get_tenant_model()) is not None:
            tenant = TenantModel._default_manager.filter(
                Q(pk__iexact=tenant_ref) | Q(schema_name=tenant_ref)
            ).first()

    if tenant is not None:
        tenant.routing = SessionInfo(reference=tenant_ref)
        request.tenant = tenant
        activate(tenant)

    return None


def route_headers(request: HttpRequest) -> HttpResponse | None:
    tenant_header = get_tenant_header()

    if not (tenant_ref := request.headers.get(tenant_header)):
        return None

    tenant: Schema | None = None

    # Checking for static tenants
    for schema, data in settings.TENANTS.items():
        if schema in ["public", "default"]:
            continue
        if tenant_ref == schema or tenant_ref == data.get("HEADER"):
            tenant = Schema.create(schema_name=schema)
            break

    # Checking for dynamic tenants
    else:
        if (TenantModel := get_tenant_model()) is not None:
            tenant = TenantModel._default_manager.filter(
                Q(pk__iexact=tenant_ref) | Q(schema_name=tenant_ref)
            ).first()

    if tenant is not None:
        tenant.routing = HeadersInfo(reference=tenant_ref)
        request.tenant = tenant
        activate(tenant)

    return None


def middleware_factory(
    handler: Callable[[HttpRequest], HttpResponse | None],
) -> Callable[[ResponseHandler], ResponseHandler]:
    @sync_and_async_middleware
    def middleware(get_response: ResponseHandler) -> ResponseHandler:
        if iscoroutinefunction(get_response):
            async_base_middleware = sync_to_async(handler)

            async def sync_middleware(request: HttpRequest) -> HttpResponse | None:
                if response := await async_base_middleware(request):
                    return response

                return await get_response(request)

            return sync_middleware

        else:

            def async_middleware(request: HttpRequest) -> HttpResponse | None:
                if response := handler(request):
                    return response

                return get_response(request)

            return async_middleware

    return middleware


DomainRoutingMiddleware = middleware_factory(route_domain)
SessionRoutingMiddleware = middleware_factory(route_session)
HeadersRoutingMiddleware = middleware_factory(route_headers)
